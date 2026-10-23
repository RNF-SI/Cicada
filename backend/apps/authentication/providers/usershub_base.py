"""
Vérification des comptes UsersHub en lisant directement sa base (#764).

C'est la seule façon de vérifier un compte GeoNature. Par l'API GeoNature
(``POST /auth/login``, retirée), le droit sur l'application CICADA n'était
jamais contrôlé : pypnusershub vérifie le droit sur le GeoNature lui-même (son
``CODE_APPLICATION``), l'``id_application`` transmis devant seulement exister
— et jusqu'à pypnusershub 3.2.x, à cause d'un bug, il ne vérifie rien du tout.
Aucune route de GeoNature ne permet de contrôler le droit sur une autre
application que la sienne. pypnusershub, bibliothèque Flask, ne s'intègre pas
à Django.

Ici CICADA refait, en lecture seule, ce que fait pypnusershub 3.3
(``LocalProvider.authenticate`` + ``User.filter_by_app``), mais sur l'application
de CICADA (``GEONATURE_AUTH_CODE_APPLICATION``) :

1. le compte est retrouvé par ``identifiant`` (``t_roles``, hors groupes) ;
2. le mot de passe est vérifié : bcrypt (``pass_plus``), sinon md5 (``pass``).
   pypnusershub réécrit un md5 juste en bcrypt ; pas nous (lecture seule) : la
   personne garde son md5 jusqu'à sa prochaine connexion à GeoNature ;
3. le compte doit avoir un profil sur l'application, directement ou par un
   groupe (``cor_role_app_profil`` + ``cor_roles``) ;
4. la fiche de l'organisme est lue dans ``bib_organismes``.

La suite (compte et organisme CICADA) est dans ``usershub.py``.

Le compte PostgreSQL n'a besoin que de SELECT sur quelques colonnes : script
``packaging/debian/usr/bin/cicada-usershub-lecture`` (vérifié par
packaging/tests/test_install_service.py). Les requêtes nomment
donc toutes leurs colonnes (un ``SELECT *`` serait refusé).
"""
import hashlib
import hmac
import logging

import bcrypt
import psycopg
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from psycopg import sql

from .usershub import IdentiteUsersHub, UsersHubErreur, UsersHubIndisponible, verifier_email

logger = logging.getLogger(__name__)

CHAMPS_FICHE_ORGANISME = (
    'uuid_organisme', 'nom_organisme', 'adresse_organisme', 'cp_organisme', 'ville_organisme',
    'tel_organisme', 'fax_organisme', 'email_organisme', 'url_organisme',
)


def est_configuree():
    return bool(settings.GEONATURE_AUTH_CODE_APPLICATION and settings.USERSHUB_DB_HOST
                and settings.USERSHUB_DB_NAME and settings.USERSHUB_DB_USER)


def _connexion():
    options = {}
    if settings.USERSHUB_DB_SSLROOTCERT:
        options['sslrootcert'] = settings.USERSHUB_DB_SSLROOTCERT
    return psycopg.connect(
        host=settings.USERSHUB_DB_HOST,
        port=settings.USERSHUB_DB_PORT,
        dbname=settings.USERSHUB_DB_NAME,
        user=settings.USERSHUB_DB_USER,
        password=settings.USERSHUB_DB_PASSWORD,
        sslmode=settings.USERSHUB_DB_SSLMODE,
        connect_timeout=settings.GEONATURE_AUTH_TIMEOUT,
        application_name='cicada-connexion-usershub',
        **options,
    )


def _requete(texte):
    """Requête dont « {s} » désigne le schéma UsersHub."""
    return sql.SQL(texte).format(s=sql.Identifier(settings.USERSHUB_DB_SCHEMA))


COMPTE = """
    SELECT id_role, identifiant, email, nom_role, prenom_role, id_organisme,
           pass_plus, pass, active
    FROM {s}.t_roles
    WHERE identifiant = %s AND groupe IS NOT TRUE
"""

# Même règle que User.filter_by_app de pypnusershub : un profil sur
# l'application, porté par le compte ou par un de ses groupes.
DROIT = """
    SELECT EXISTS (
        SELECT 1
        FROM {s}.cor_role_app_profil p
        JOIN {s}.t_applications a ON a.id_application = p.id_application
        WHERE a.code_application = %(code)s
          AND (p.id_role = %(id_role)s
               OR p.id_role IN (SELECT id_role_groupe FROM {s}.cor_roles
                                WHERE id_role_utilisateur = %(id_role)s))
    )
"""

# Pour la commande verifier_usershub : l'accès qu'aurait chaque compte, sans
# mot de passe (même règle que DROIT).
ACCES = """
    SELECT u.id_role, lower(u.email), u.active IS NOT FALSE,
           EXISTS (
               SELECT 1
               FROM {s}.cor_role_app_profil p
               JOIN {s}.t_applications a ON a.id_application = p.id_application
               WHERE a.code_application = %(code)s
                 AND (p.id_role = u.id_role
                      OR p.id_role IN (SELECT id_role_groupe FROM {s}.cor_roles
                                       WHERE id_role_utilisateur = u.id_role)))
    FROM {s}.t_roles u
    WHERE u.groupe IS NOT TRUE
      AND (u.id_role = ANY(%(ids)s) OR lower(u.email) = ANY(%(emails)s))
"""

ORGANISME = """
    SELECT uuid_organisme, nom_organisme, adresse_organisme, cp_organisme, ville_organisme,
           tel_organisme, fax_organisme, email_organisme, url_organisme
    FROM {s}.bib_organismes
    WHERE id_organisme = %s
"""


def mot_de_passe_valide(password, pass_plus, pass_md5):
    """Comme ``PasswordMixin.check_password`` de pypnusershub, sans réécriture."""
    if pass_plus:
        try:
            return bcrypt.checkpw(password.encode('utf8'), pass_plus.encode('utf8'))
        except ValueError:
            # Empreinte illisible : on retombe sur le md5 s'il existe.
            logger.error("Connexion UsersHub : empreinte bcrypt illisible")
    if pass_md5:
        return hmac.compare_digest(hashlib.md5(password.encode('utf8')).hexdigest(), pass_md5)
    return False


def _refus():
    return UsersHubErreur(_("Identifiant ou mot de passe incorrect."))


def authentifier(login, password):
    """Vérifie le compte dans la base UsersHub ; rend une IdentiteUsersHub."""
    try:
        with _connexion() as connexion, connexion.cursor() as curseur:
            curseur.execute(_requete(COMPTE), (login,))
            lignes = curseur.fetchall()
            if len(lignes) > 1:
                # pypnusershub échoue aussi (scalar_one) : identifiant ambigu.
                logger.error("Connexion UsersHub : identifiant porté par %s comptes", len(lignes))
                raise _refus()
            if not lignes:
                raise _refus()
            (id_role, identifiant, email, nom, prenom, id_organisme,
             pass_plus, pass_md5, actif) = lignes[0]

            if not mot_de_passe_valide(password, pass_plus, pass_md5):
                raise _refus()
            if actif is False:
                raise UsersHubErreur(
                    _("Votre compte %(libelle)s est désactivé.") % {'libelle': settings.GEONATURE_AUTH_LIBELLE},
                    status_code=403,
                )

            curseur.execute(_requete(DROIT), {'code': settings.GEONATURE_AUTH_CODE_APPLICATION,
                                              'id_role': id_role})
            if not curseur.fetchone()[0]:
                raise UsersHubErreur(
                    _("Votre compte %(libelle)s n'a pas accès à CICADA. "
                      "Demandez cet accès à l'administrateur de %(libelle)s.")
                    % {'libelle': settings.GEONATURE_AUTH_LIBELLE},
                    status_code=403,
                )

            fiche = None
            if id_organisme is not None and int(id_organisme) not in settings.GEONATURE_AUTH_ORGANISMES_EXCLUS:
                curseur.execute(_requete(ORGANISME), (id_organisme,))
                ligne = curseur.fetchone()
                if ligne is None:
                    logger.error("Connexion UsersHub : organisme %s introuvable", id_organisme)
                elif not ligne[0]:
                    logger.error("Connexion UsersHub : organisme %s sans uuid_organisme", id_organisme)
                else:
                    fiche = dict(zip(CHAMPS_FICHE_ORGANISME, ligne))
                    fiche['uuid_organisme'] = str(fiche['uuid_organisme'])
    except psycopg.OperationalError as exc:
        # Jamais le message brut : il peut citer l'hôte et le compte.
        logger.error("Connexion UsersHub : base %s injoignable (%s)",
                     settings.USERSHUB_DB_HOST, type(exc).__name__)
        raise UsersHubIndisponible()
    except psycopg.Error as exc:
        # Droits du compte de lecture insuffisants, schéma inattendu…
        logger.error("Connexion UsersHub : lecture de la base refusée (%s : %s)",
                     type(exc).__name__, str(exc).splitlines()[0] if str(exc) else '')
        raise UsersHubIndisponible()

    identite = IdentiteUsersHub(
        id_role=int(id_role),
        email=(email or '').strip(),
        identifiant=(identifiant or '').strip(),
        nom=(nom or '').strip(),
        prenom=(prenom or '').strip(),
        id_organisme=id_organisme,
        fiche_organisme=fiche,
    )
    verifier_email(identite)
    return identite


def acces_des_comptes(ids, emails):
    """Lignes (id_role, email, actif, droit) des comptes UsersHub désignés par
    leur id ou leur email. Lève UsersHubIndisponible comme authentifier()."""
    try:
        with _connexion() as connexion, connexion.cursor() as curseur:
            curseur.execute(_requete(ACCES), {'code': settings.GEONATURE_AUTH_CODE_APPLICATION,
                                              'ids': list(ids), 'emails': [e.lower() for e in emails]})
            return curseur.fetchall()
    except psycopg.Error as exc:
        logger.error("Vérification UsersHub : %s", type(exc).__name__)
        raise UsersHubIndisponible()
