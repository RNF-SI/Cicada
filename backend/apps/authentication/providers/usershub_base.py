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
from django.utils.translation import gettext_lazy as _
from psycopg import sql

from .. import reglages
from .usershub import IdentiteUsersHub, UsersHubErreur, UsersHubIndisponible, verifier_email

logger = logging.getLogger(__name__)

CHAMPS_FICHE_ORGANISME = (
    'uuid_organisme', 'nom_organisme', 'adresse_organisme', 'cp_organisme', 'ville_organisme',
    'tel_organisme', 'fax_organisme', 'email_organisme', 'url_organisme',
)


def est_configuree(r=None):
    return (r or reglages.actuels()).est_configuree()


def _connexion(r):
    options = {}
    if r.db_sslrootcert:
        options['sslrootcert'] = r.db_sslrootcert
    return psycopg.connect(
        host=r.db_host,
        port=r.db_port,
        dbname=r.db_name,
        user=r.db_user,
        password=r.db_password,
        sslmode=r.db_sslmode,
        connect_timeout=r.timeout,
        application_name='cicada-connexion-usershub',
        **options,
    )


def _requete(texte, r):
    """Requête dont « {s} » désigne le schéma UsersHub."""
    return sql.SQL(texte).format(s=sql.Identifier(r.schema))


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
    r = reglages.actuels()
    try:
        with _connexion(r) as connexion, connexion.cursor() as curseur:
            curseur.execute(_requete(COMPTE, r), (login,))
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
                    _("Votre compte %(libelle)s est désactivé.") % {'libelle': r.libelle},
                    status_code=403,
                )

            curseur.execute(_requete(DROIT, r), {'code': r.code_application,
                                              'id_role': id_role})
            if not curseur.fetchone()[0]:
                raise UsersHubErreur(
                    _("Votre compte %(libelle)s n'a pas accès à CICADA. "
                      "Demandez cet accès à l'administrateur de %(libelle)s.")
                    % {'libelle': r.libelle},
                    status_code=403,
                )

            fiche = None
            if id_organisme is not None and int(id_organisme) not in r.organismes_exclus:
                curseur.execute(_requete(ORGANISME, r), (id_organisme,))
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
                     r.db_host, type(exc).__name__)
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


def acces_des_comptes(ids, emails, r=None):
    """Lignes (id_role, email, actif, droit) des comptes UsersHub désignés par
    leur id ou leur email. Lève UsersHubIndisponible comme authentifier()."""
    r = r or reglages.actuels()
    try:
        with _connexion(r) as connexion, connexion.cursor() as curseur:
            curseur.execute(_requete(ACCES, r), {'code': r.code_application,
                                                 'ids': list(ids), 'emails': [e.lower() for e in emails]})
            return curseur.fetchall()
    except psycopg.Error as exc:
        logger.error("Vérification UsersHub : %s", type(exc).__name__)
        raise UsersHubIndisponible()


def bilan_des_comptes(r=None):
    """
    Qui, parmi les comptes CICADA actifs, pourra se connecter avec la
    configuration ``r`` ? Sans rien modifier (commande verifier_usershub et
    bouton « Tester » des paramètres, #769).

    Rend ``{'total', 'autorises', 'refuses', 'super_admins_autorises',
    'comptes': [{'id', 'email', 'super_admin', 'motif'}]}`` — ``motif`` vaut
    None (autorisé), 'absent', 'inactif' ou 'sans_droit'.
    """
    from apps.users.models import Role

    r = r or reglages.actuels()
    comptes = list(Role.objects.filter(is_active=True, is_anonymized=False).order_by('email')
                   .values('id_role', 'email', 'usershub_id_role', 'is_superuser', 'role_level'))
    lignes = acces_des_comptes(
        [c['usershub_id_role'] for c in comptes if c['usershub_id_role']],
        [c['email'] for c in comptes if not c['usershub_id_role'] and c['email']],
        r,
    )
    par_id = {ligne[0]: ligne for ligne in lignes}
    par_email = {}
    for ligne in lignes:
        par_email.setdefault(ligne[1], []).append(ligne)

    resultat = []
    for compte in comptes:
        if compte['usershub_id_role']:
            trouve = par_id.get(compte['usershub_id_role'])
        else:
            # Retrouvé par email à la première connexion (compte_pour) :
            # plusieurs comptes UsersHub au même email, celui qui se
            # connecte décidera ; on retient le meilleur cas.
            candidats = par_email.get((compte['email'] or '').lower(), [])
            trouve = max(candidats, key=lambda l: (l[3], l[2]), default=None)
        if trouve is None:
            motif = 'absent'
        elif not trouve[2]:
            motif = 'inactif'
        elif not trouve[3]:
            motif = 'sans_droit'
        else:
            motif = None
        resultat.append({
            'id': compte['id_role'], 'email': compte['email'], 'motif': motif,
            'super_admin': bool(compte['is_superuser'] or compte['role_level'] == 'super_admin'),
        })
    autorises = [c for c in resultat if c['motif'] is None]
    return {
        'total': len(resultat),
        'autorises': len(autorises),
        'refuses': len(resultat) - len(autorises),
        'super_admins_autorises': sum(c['super_admin'] for c in autorises),
        'comptes': resultat,
    }


class ErreurDiagnostic(Exception):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code
        self.message = message


# Causes fréquentes, reconnues dans le message de libpq (qui ne contient
# jamais le mot de passe) : un message clair vaut mieux qu'une trace.
CAUSES = (
    ('password authentication failed', 'mot_de_passe',
     "Mot de passe refusé pour le compte de lecture : ressaisissez celui affiché par cicada-usershub-lecture."),
    ('no pg_hba.conf entry', 'pg_hba',
     "Le serveur de la base refuse ce serveur CICADA (pg_hba.conf) : relancez cicada-usershub-lecture "
     "avec l'adresse de ce serveur (--client), ou en connexion chiffrée si la ligne est en hostssl."),
    ('does not exist', 'base_ou_compte',
     "La base ou le compte de lecture n'existe pas sur ce serveur : vérifiez le nom de la base et du compte."),
    ('server does not support ssl', 'ssl',
     "Le serveur PostgreSQL n'accepte pas le chiffrement : activez ssl = on, ou choisissez « prefer » "
     "si la base est sur ce serveur."),
    ('connection refused', 'refusee',
     "Rien n'écoute à cette adresse : vérifiez l'hôte et le port, et listen_addresses côté PostgreSQL."),
    ('timeout expired', 'delai',
     "Pas de réponse : un pare-feu bloque sans doute le port PostgreSQL depuis ce serveur."),
    ('could not translate host name', 'hote',
     "Nom d'hôte inconnu : vérifiez l'adresse de la base."),
)


def diagnostiquer(r):
    """
    Connexion de test : ``{'chiffree': bool, 'application': bool}``, ou
    ErreurDiagnostic avec une cause lisible. Ne lit aucun compte.
    """
    try:
        with _connexion(r) as connexion, connexion.cursor() as curseur:
            chiffree = bool(connexion.pgconn.ssl_in_use)
            curseur.execute(_requete("SELECT EXISTS (SELECT 1 FROM {s}.t_applications "
                                     "WHERE code_application = %s)", r), (r.code_application,))
            application = curseur.fetchone()[0]
    except psycopg.OperationalError as exc:
        texte = str(exc).lower()
        logger.error("Test UsersHub : base %s injoignable (%s)", r.db_host, type(exc).__name__)
        for motif, code, message in CAUSES:
            if motif in texte:
                raise ErreurDiagnostic(code, message)
        raise ErreurDiagnostic('injoignable', "Base UsersHub injoignable : " + (str(exc).strip().splitlines() or [''])[-1][:300])
    except psycopg.Error as exc:
        logger.error("Test UsersHub : lecture refusée (%s)", type(exc).__name__)
        raise ErreurDiagnostic(
            'lecture_refusee',
            "Connexion établie, mais lecture des tables UsersHub refusée : relancez cicada-usershub-lecture "
            "sur le serveur de la base (droits du compte), ou vérifiez qu'il s'agit bien de la base de UsersHub.")
    return {'chiffree': chiffree, 'application': bool(application)}
