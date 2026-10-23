"""
Connexion par un GeoNature / UsersHub (#689) et rattachement à l'organisme (#691).

Déroulé d'une connexion :

``GEONATURE_AUTH_URL`` est l'adresse de l'**API** GeoNature, c'est-à-dire la
valeur ``API_ENDPOINT`` de sa configuration : souvent ``https://…/api`` derrière
un Apache, parfois sans suffixe (``http://127.0.0.1:5000`` en développement).

1. ``POST {GEONATURE_AUTH_URL}/auth/login`` vérifie l'identifiant et le mot
   de passe (serveur → serveur : le navigateur ne parle jamais à GeoNature).
   La réponse donne ``id_role``, l'email, le nom et ``id_organisme``, mais pas
   l'organisme lui-même.
2. ``GET {GEONATURE_AUTH_URL}/users/organism/<id>``, avec le jeton qui
   vient d'être délivré, donne l'``uuid_organisme`` et la fiche (GeoNature
   >= 2.17.0). L'uuid est la clé commune aux deux bases : les ``id_organisme``
   sont des séquences locales et ne coïncident pas.
3. Le compte CICADA est retrouvé par ``usershub_id_role``, sinon par email,
   sinon créé ; l'organisme est retrouvé par uuid, sinon créé.

Rien n'est synchronisé en dehors des connexions : un nouvel organisme UsersHub
apparaît dans CICADA à la première connexion d'un de ses membres.

Le jeton GeoNature ne sert qu'à l'étape 2 et n'est jamais conservé.

Source 'base' (#764, ``GEONATURE_AUTH_SOURCE=base``) : les étapes 1 et 2 sont
remplacées par une lecture de la base UsersHub (``usershub_base.py``), qui
contrôle le droit sur l'application CICADA ; l'étape 3 est la même.
"""
import logging
from dataclasses import dataclass, field

import requests
from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils.translation import gettext_lazy as _

from apps.users.models import BibOrganismes, Role

logger = logging.getLogger(__name__)


class UsersHubErreur(Exception):
    """Échec de connexion à présenter tel quel à l'utilisateur."""

    def __init__(self, message, status_code=401):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class UsersHubIndisponible(UsersHubErreur):
    """GeoNature ne répond pas, ou pas comme prévu."""

    def __init__(self, message=None):
        super().__init__(
            message or _("Le service de connexion %(libelle)s est indisponible. "
                         "Réessayez plus tard ou connectez-vous avec votre email.")
            % {'libelle': settings.GEONATURE_AUTH_LIBELLE},
            status_code=502,
        )


def par_la_base():
    """Comptes vérifiés dans la base UsersHub (#764) plutôt que par l'API GeoNature."""
    return settings.GEONATURE_AUTH_SOURCE == 'base'


def est_active():
    """Mode 'geonature' choisi ET réglages de la source choisie présents."""
    from . import GEONATURE, mode_connexion
    if mode_connexion() != GEONATURE:
        return False
    if par_la_base():
        from . import usershub_base
        return usershub_base.est_configuree()
    return bool(settings.GEONATURE_AUTH_URL and settings.GEONATURE_AUTH_ID_APPLICATION)


def verifier(login, password):
    """Vérifie le compte UsersHub par la source configurée ; rend une IdentiteUsersHub."""
    if par_la_base():
        from . import usershub_base
        return usershub_base.authentifier(login, password)
    return authentifier(login, password)


@dataclass
class IdentiteUsersHub:
    id_role: int
    email: str
    identifiant: str = ''
    nom: str = ''
    prenom: str = ''
    id_organisme: int | None = None
    jeton: str = field(default='', repr=False)
    # 'api' : organisme lu par l'API GeoNature avec le jeton ; 'base' : fiche
    # déjà lue dans la base UsersHub (None si absente ou exclue).
    source: str = 'api'
    fiche_organisme: dict | None = field(default=None, repr=False)


# ---------------------------------------------------------------------------
# Appels à GeoNature
# ---------------------------------------------------------------------------

def _url(chemin):
    return f"{settings.GEONATURE_AUTH_URL}{chemin}"


# Sans « Accept: application/json », GeoNature répond à un refus par une
# redirection vers sa page de connexion (302) au lieu d'un 401.
ENTETES = {'Accept': 'application/json'}


def authentifier(login, password):
    """Vérifie l'identifiant et le mot de passe auprès de GeoNature."""
    try:
        reponse = requests.post(
            _url('/auth/login'),
            json={
                'login': login,
                'password': password,
                'id_application': settings.GEONATURE_AUTH_ID_APPLICATION,
            },
            headers=ENTETES,
            timeout=settings.GEONATURE_AUTH_TIMEOUT,
            allow_redirects=False,
        )
    except requests.RequestException as exc:
        # Jamais le corps de la requête dans les journaux : il porte le mot de passe.
        logger.error("Connexion GeoNature : %s injoignable (%s)", settings.GEONATURE_AUTH_URL, type(exc).__name__)
        raise UsersHubIndisponible()

    if reponse.status_code in (400, 401, 403, 404):
        raise UsersHubErreur(_("Identifiant ou mot de passe incorrect."))
    if 300 <= reponse.status_code < 400:
        # Redirection vers la page de connexion de GeoNature = refus.
        # Toute autre redirection trahit une adresse mal réglée
        # (http → https, API_ENDPOINT sans « /api »…).
        destination = reponse.headers.get('Location', '')
        if 'login?next=' in destination:
            raise UsersHubErreur(_("Identifiant ou mot de passe incorrect."))
        logger.error("Connexion GeoNature : redirection inattendue vers %s — "
                     "vérifier GEONATURE_AUTH_URL", destination)
        raise UsersHubIndisponible()
    if reponse.status_code != 200:
        logger.error("Connexion GeoNature : réponse %s inattendue au login", reponse.status_code)
        raise UsersHubIndisponible()

    try:
        donnees = reponse.json()
        user = donnees['user']
        identite = IdentiteUsersHub(
            id_role=int(user['id_role']),
            email=(user.get('email') or '').strip(),
            identifiant=(user.get('identifiant') or '').strip(),
            nom=(user.get('nom_role') or '').strip(),
            prenom=(user.get('prenom_role') or '').strip(),
            id_organisme=user.get('id_organisme'),
            jeton=donnees.get('token') or '',
        )
    except (ValueError, KeyError, TypeError):
        logger.error("Connexion GeoNature : réponse de login illisible")
        raise UsersHubIndisponible()

    verifier_email(identite)
    return identite


def verifier_email(identite):
    """Un compte UsersHub sans email ne peut pas devenir un compte CICADA."""
    if not identite.email or '@' not in identite.email:
        raise UsersHubErreur(
            _("Votre compte %(libelle)s n'a pas d'adresse email : il ne peut pas être "
              "utilisé pour se connecter à CICADA. Contactez l'administrateur de %(libelle)s.")
            % {'libelle': settings.GEONATURE_AUTH_LIBELLE},
            status_code=403,
        )


def lire_organisme(id_organisme, jeton):
    """
    Fiche de l'organisme dans GeoNature, ou None si elle ne peut pas être lue.

    Ne lève jamais : un organisme illisible ne doit pas empêcher la connexion.
    """
    try:
        reponse = requests.get(
            _url(f'/users/organism/{int(id_organisme)}'),
            headers={**ENTETES, 'Authorization': f'Bearer {jeton}'},
            timeout=settings.GEONATURE_AUTH_TIMEOUT,
            allow_redirects=False,
        )
    except requests.RequestException as exc:
        logger.error("Connexion GeoNature : organisme %s illisible (%s)", id_organisme, type(exc).__name__)
        return None
    if reponse.status_code == 404:
        logger.error(
            "Connexion GeoNature : GET /users/organism/%s introuvable — "
            "organisme supprimé, ou GeoNature antérieur à 2.17.0", id_organisme,
        )
        return None
    if reponse.status_code != 200:
        logger.error("Connexion GeoNature : organisme %s, réponse %s", id_organisme, reponse.status_code)
        return None
    try:
        fiche = reponse.json()
    except ValueError:
        return None
    if not isinstance(fiche, dict) or not fiche.get('uuid_organisme'):
        logger.error("Connexion GeoNature : organisme %s sans uuid_organisme", id_organisme)
        return None
    return fiche


# ---------------------------------------------------------------------------
# Rattachement côté CICADA
# ---------------------------------------------------------------------------

CHAMPS_ORGANISME = (
    'adresse_organisme', 'cp_organisme', 'ville_organisme', 'tel_organisme',
    'fax_organisme', 'email_organisme', 'url_organisme',
)


def organisme_pour(identite):
    """
    Organisme CICADA correspondant à l'organisme UsersHub de la personne.

    Retrouvé par uuid, créé s'il n'existe pas. None si la personne n'a pas
    d'organisme, si c'est un pseudo-organisme exclu, ou si GeoNature n'a pas pu
    le décrire.
    """
    id_organisme = identite.id_organisme
    if id_organisme is None or int(id_organisme) in settings.GEONATURE_AUTH_ORGANISMES_EXCLUS:
        return None

    if identite.source == 'base':
        fiche = identite.fiche_organisme
    else:
        fiche = lire_organisme(id_organisme, identite.jeton)
    if fiche is None:
        return None

    organisme = BibOrganismes.objects.filter(uuid_organisme=fiche['uuid_organisme']).first()
    if organisme is not None:
        return organisme

    nom = (fiche.get('nom_organisme') or '').strip()
    if not nom:
        return None
    valeurs = {c: (fiche.get(c) or None) for c in CHAMPS_ORGANISME}
    # Champs à longueur bornée côté CICADA : on tronque plutôt que d'échouer.
    for champ, longueur in (('cp_organisme', 10), ('ville_organisme', 100),
                            ('tel_organisme', 20), ('fax_organisme', 20),
                            ('email_organisme', 254), ('url_organisme', 200)):
        if valeurs[champ]:
            valeurs[champ] = str(valeurs[champ])[:longueur]
    try:
        with transaction.atomic():
            organisme = BibOrganismes.objects.create(
                uuid_organisme=fiche['uuid_organisme'],
                nom_organisme=nom[:255],
                additional_data={'source': 'usershub', 'id_organisme_usershub': int(id_organisme)},
                **valeurs,
            )
    except IntegrityError:
        # Créé entre-temps par une connexion simultanée d'un collègue.
        organisme = BibOrganismes.objects.filter(uuid_organisme=fiche['uuid_organisme']).first()
    else:
        logger.info("Connexion GeoNature : organisme « %s » créé (UsersHub n° %s)", nom, id_organisme)
    return organisme


def compte_pour(identite):
    """
    Compte CICADA de la personne : retrouvé par id UsersHub, sinon par email,
    sinon créé. Lève UsersHubErreur si le compte ne peut pas être utilisé.

    Les droits locaux (rôle, référents, sites, plans) ne sont jamais touchés :
    seuls l'identité et l'organisme viennent de UsersHub.
    """
    email = Role.objects.normalize_email(identite.email)

    with transaction.atomic():
        compte = (
            Role.objects.select_for_update().filter(usershub_id_role=identite.id_role).first()
            or Role.objects.select_for_update().filter(
                email__iexact=email, usershub_id_role__isnull=True, is_anonymized=False,
            ).first()
        )
        if compte is None and Role.objects.filter(email__iexact=email).exists():
            # Même email qu'un compte déjà relié à un AUTRE compte UsersHub.
            logger.error(
                "Connexion GeoNature : l'email du compte UsersHub %s est déjà relié "
                "à un autre compte UsersHub", identite.id_role,
            )
            raise UsersHubErreur(
                _("Un autre compte CICADA utilise déjà cette adresse email. "
                  "Contactez un administrateur."),
                status_code=409,
            )

        organisme = organisme_pour(identite)

        if compte is None:
            compte = Role(
                email=email,
                usershub_id_role=identite.id_role,
                nom_role=identite.nom[:50] or None,
                prenom_role=identite.prenom[:50] or None,
                identifiant=identite.identifiant[:100] or None,
                id_organisme=organisme,
                role_level='utilisateur',
                active=True,
                pending_validation=False,
            )
            # Connexion par UsersHub seulement, jusqu'à ce que la personne
            # choisisse un mot de passe CICADA (« mot de passe oublié »).
            compte.set_unusable_password()
            compte.save()
            logger.info("Connexion GeoNature : compte créé (UsersHub n° %s)", identite.id_role)
            return compte

        if not compte.active or not compte.is_active:
            raise UsersHubErreur(_("Ce compte est désactivé."), status_code=403)
        if compte.pending_validation:
            raise UsersHubErreur(
                _("Votre compte est en attente de validation par un administrateur. "
                  "Vous recevrez un email lorsque votre compte sera activé."),
                status_code=403,
            )

        compte.usershub_id_role = identite.id_role
        if identite.nom:
            compte.nom_role = identite.nom[:50]
        if identite.prenom:
            compte.prenom_role = identite.prenom[:50]
        if compte.email.lower() != email.lower():
            if Role.objects.filter(email__iexact=email).exclude(pk=compte.pk).exists():
                logger.warning(
                    "Connexion GeoNature : nouvel email du compte UsersHub %s déjà pris "
                    "par un autre compte — email CICADA conservé", identite.id_role,
                )
            else:
                compte.email = email
        # UsersHub fait foi sur l'organisme, mais un organisme illisible
        # (GeoNature trop ancien, panne) ne retire pas celui déjà connu.
        if organisme is not None:
            compte.id_organisme = organisme
        compte.save()
        return compte
