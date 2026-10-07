"""
Configuration effective du raccordement au hub d'exploration (#696, #698).

Une instance se raccorde au hub de deux façons :

- **par l'environnement** (`CICADA_HUB_URL`, `CICADA_HUB_PUSH_TOKEN`,
  `CICADA_HUB_READ_TOKEN`) — le raccordement historique, que garde une instance
  à qui RNF a remis ses jetons (banc d'essai, instances pionnières) ;
- **par adhésion** — l'instance demande à rejoindre l'exploration nationale
  depuis `Administration > Paramètres`, RNF accepte depuis l'admin de l'API de
  suivi, et le hub enrôle les empreintes que l'instance a fournies.

Tout le code qui parle au hub passe par ce module (`hub_url()`,
`jeton_depot()`, `jeton_lecture()`) au lieu de lire les réglages : une lecture
directe de `settings.CICADA_HUB_PUSH_TOKEN` ignorerait silencieusement une
adhésion acceptée, et l'instance continuerait de se croire non raccordée.

## Le jeton du hub ne voyage jamais

L'instance tire elle-même ses deux jetons, les garde chiffrés en base, et
n'envoie que leurs **empreintes SHA-256** — la seule chose que le hub stocke de
toute façon. Le **code de vérification**, recalculé à l'identique par le suivi,
est comparé de vive voix par RNF avec la structure avant d'accepter : il bloque
une demande faite au nom d'une autre structure, et une substitution
d'empreintes en route.

Aucun jeton ni aucune empreinte ne sort de ce module dans une réponse d'API ou
une ligne de journal.
"""

import base64
import hashlib
import logging
import re
import secrets

import requests
from django.conf import settings
from django.utils import timezone

from .models import PublicationHub, RaccordementHub

logger = logging.getLogger(__name__)

#: Délai des appels de diagnostic et d'adhésion : ils sont déclenchés depuis
#: une page d'administration, un utilisateur attend la réponse.
DELAI = 5

#: Même règle que l'installeur et le hub (`VALIDATEUR_IDENTIFIANT`).
IDENTIFIANT_VALIDE = re.compile(r'^[a-z0-9][a-z0-9-]{0,49}$')

#: Nombre de publications rendues dans l'état (le modèle en garde davantage).
PUBLICATIONS_AFFICHEES = 10

SOURCE_ENVIRONNEMENT = 'environnement'
SOURCE_ADHESION = 'adhesion'


class ErreurRaccordement(Exception):
    """Échec d'une opération de raccordement, porteur d'une clé d'erreur."""

    def __init__(self, cle, message, statut_http=400):
        super().__init__(message)
        self.cle = cle
        self.message = message
        self.statut_http = statut_http


# --------------------------------------------------------------------------- #
# Formules partagées avec l'API de suivi — à garder À L'IDENTIQUE
# --------------------------------------------------------------------------- #

def empreinte(jeton):
    """Empreinte SHA-256 d'un jeton — même formule que le hub."""
    return hashlib.sha256(jeton.encode('utf-8')).hexdigest()


def code_verification(instance_token, instance_id, empreinte_depot, empreinte_lecture):
    """
    6 caractères base32 présentés « ABC-DEF ».

    Dérivé de l'**empreinte** du jeton de suivi (pas du jeton) pour rester
    calculable si le suivi ne stocke plus que des empreintes (#697). Le suivi
    recalcule ce code de son côté : la moindre divergence de formule rendrait
    toute comparaison de vive voix impossible.
    """
    source = f"{empreinte(instance_token)}:{instance_id}:{empreinte_depot}:{empreinte_lecture}"
    brut = base64.b32encode(hashlib.sha256(source.encode('utf-8')).digest()).decode('ascii')[:6]
    return f"{brut[:3]}-{brut[3:]}"


def nouveau_jeton():
    """Un jeton de 384 bits — comme `Instance.nouveau_jeton()` côté hub."""
    return secrets.token_urlsafe(48)


# --------------------------------------------------------------------------- #
# Chiffrement des jetons obtenus par adhésion
# --------------------------------------------------------------------------- #

def _fernet():
    """
    Clé dérivée de la `SECRET_KEY`.

    Pas de clé dédiée à gérer : une copie de la base ne suffit pas à publier
    au nom de la structure, il faut aussi la configuration du serveur. Le
    suffixe sépare cet usage de tout autre dérivé de la même clé.
    """
    from cryptography.fernet import Fernet

    cle = base64.urlsafe_b64encode(
        hashlib.sha256((settings.SECRET_KEY + ':cicada-hub-jetons').encode('utf-8')).digest()
    )
    return Fernet(cle)


def chiffrer(jeton):
    return _fernet().encrypt(jeton.encode('utf-8')).decode('ascii')


def dechiffrer(texte):
    """
    Le jeton en clair, ou ``None`` s'il est absent ou indéchiffrable.

    Indéchiffrable = la `SECRET_KEY` a changé depuis l'adhésion. Ce n'est pas
    une panne à faire remonter dans une vue d'exploration : le jeton est
    considéré absent, et le diagnostic de la page de raccordement le dit.
    """
    if not texte:
        return None
    from cryptography.fernet import InvalidToken

    try:
        return _fernet().decrypt(texte.encode('ascii')).decode('utf-8')
    except (InvalidToken, ValueError):
        logger.warning(
            "Jeton du hub indéchiffrable (SECRET_KEY modifiée depuis l'adhésion ?) "
            "— considéré absent."
        )
        return None


# --------------------------------------------------------------------------- #
# Configuration effective
# --------------------------------------------------------------------------- #

def raccordement():
    return RaccordementHub.charger()


def jetons_environnement():
    """Des jetons sont-ils fournis par l'environnement ?"""
    return bool(settings.CICADA_HUB_PUSH_TOKEN or settings.CICADA_HUB_READ_TOKEN)


def hub_url(ligne=None):
    """URL du hub : l'environnement d'abord, sinon celle reçue à l'adhésion."""
    if settings.CICADA_HUB_URL:
        return settings.CICADA_HUB_URL.rstrip('/')
    ligne = ligne or raccordement()
    return (ligne.hub_url or '').rstrip('/')


def _jeton_adhesion(champ, ligne=None):
    """
    Jeton tiré à l'adhésion — **seulement si elle est acceptée**.

    Avant l'acceptation, le hub ne connaît pas encore l'empreinte : s'en servir
    produirait des 403 que rien n'expliquerait à l'écran.
    """
    ligne = ligne or raccordement()
    if ligne.adhesion_statut != RaccordementHub.STATUT_ACCEPTEE:
        return None
    return dechiffrer(getattr(ligne, champ))


def jeton_depot(ligne=None):
    return settings.CICADA_HUB_PUSH_TOKEN or _jeton_adhesion('jeton_depot_chiffre', ligne)


def jeton_lecture(ligne=None):
    return settings.CICADA_HUB_READ_TOKEN or _jeton_adhesion('jeton_lecture_chiffre', ligne)


def source_jetons(ligne=None):
    """D'où viennent les jetons effectifs : `environnement`, `adhesion` ou ``None``."""
    if jetons_environnement():
        return SOURCE_ENVIRONNEMENT
    ligne = ligne or raccordement()
    if ligne.adhesion_statut == RaccordementHub.STATUT_ACCEPTEE:
        return SOURCE_ADHESION
    return None


def identite_valide():
    """
    L'identité de l'instance permet-elle d'adhérer ?

    `local` est la valeur de repli d'une instance non configurée : elle ne
    désigne personne, et deux instances qui la partageraient écraseraient
    mutuellement leurs plans sur le hub.
    """
    identifiant = settings.CICADA_INSTANCE_ID or ''
    return bool(
        identifiant != 'local'
        and IDENTIFIANT_VALIDE.match(identifiant)
        and (settings.CICADA_INSTANCE_LABEL or '').strip()
    )


# --------------------------------------------------------------------------- #
# Dialogue avec l'API de suivi
# --------------------------------------------------------------------------- #

def _suivi():
    """URL et jeton du suivi ; erreur explicite sans jeton."""
    from apps.system.tracking import instance_token, tracking_api_url

    jeton = instance_token()
    if not jeton:
        raise ErreurRaccordement(
            'jeton_suivi_absent',
            "Jeton de suivi de l'instance introuvable (/etc/cicada/instance_token).",
        )
    return tracking_api_url(), jeton


def actualiser_adhesion(ligne=None):
    """
    Relit auprès du suivi l'état d'une adhésion en attente.

    Renvoie une clé d'erreur, ou ``None`` si l'actualisation a réussi (ou n'avait
    pas lieu d'être). Ne lève jamais : une page d'administration doit pouvoir
    s'afficher même si le suivi est injoignable.
    """
    ligne = ligne or raccordement()
    if ligne.adhesion_statut != RaccordementHub.STATUT_EN_ATTENTE:
        return None
    try:
        url, jeton = _suivi()
    except ErreurRaccordement as erreur:
        return erreur.cle
    try:
        reponse = requests.get(
            f"{url}/instances/adhesion-hub/",
            headers={'X-Instance-Token': jeton}, timeout=DELAI,
        )
    except requests.RequestException as erreur:
        logger.warning("API de suivi injoignable pour l'adhésion au hub : %s", type(erreur).__name__)
        return 'suivi_indisponible'
    if reponse.status_code == 404:
        return 'erreur_inconnue'
    if reponse.status_code != 200:
        logger.warning("API de suivi : actualisation de l'adhésion → %s", reponse.status_code)
        return 'suivi_indisponible'
    try:
        corps = reponse.json()
    except ValueError:
        return 'suivi_indisponible'

    statut = corps.get('statut')
    if statut not in (
        RaccordementHub.STATUT_EN_ATTENTE, RaccordementHub.STATUT_ACCEPTEE,
        RaccordementHub.STATUT_REFUSEE,
    ):
        return 'suivi_indisponible'
    ligne.adhesion_statut = statut
    ligne.adhesion_motif = corps.get('motif_refus') or ''
    if statut == RaccordementHub.STATUT_ACCEPTEE and corps.get('hub_url'):
        ligne.hub_url = corps['hub_url'].rstrip('/')
    ligne.adhesion_actualisee_le = timezone.now()
    ligne.save()
    if statut != RaccordementHub.STATUT_EN_ATTENTE:
        logger.info("Adhésion au hub : statut « %s » reçu du suivi.", statut)
    return None


def adhesion_possible(ligne=None):
    ligne = ligne or raccordement()
    from apps.system.tracking import instance_token

    return bool(
        identite_valide()
        and not jetons_environnement()
        and instance_token()
        and ligne.adhesion_statut in (RaccordementHub.STATUT_AUCUNE, RaccordementHub.STATUT_REFUSEE)
    )


def demander_adhesion():
    """
    Tire deux jetons, envoie leurs empreintes au suivi et enregistre la demande.

    Les jetons ne sont enregistrés qu'**après** la réponse du suivi, et
    seulement si le code qu'il a calculé est celui calculé ici : une demande
    qui échoue laisse l'état précédent intact. Un suivi qui aurait enregistré
    la demande sans que la réponse arrive n'est pas un problème — la demande
    suivante remplace une demande en attente.
    """
    ligne = raccordement()
    if jetons_environnement():
        raise ErreurRaccordement(
            'jetons_environnement',
            "Des jetons du hub sont déjà fournis par l'environnement : l'adhésion "
            "ne concerne que les instances sans jetons.", 409,
        )
    if ligne.adhesion_statut == RaccordementHub.STATUT_ACCEPTEE:
        raise ErreurRaccordement('deja_acceptee', "L'adhésion est déjà acceptée.", 409)
    if not identite_valide():
        raise ErreurRaccordement(
            'identite_manquante',
            "Renseignez CICADA_INSTANCE_ID et CICADA_INSTANCE_LABEL dans "
            "/var/lib/cicada/.env (puis `rebuild_search_index --purge` si l'index "
            "existe déjà) avant de demander l'adhésion.",
        )
    url, jeton_suivi = _suivi()

    depot, lecture = nouveau_jeton(), nouveau_jeton()
    empreinte_depot, empreinte_lecture = empreinte(depot), empreinte(lecture)
    code = code_verification(
        jeton_suivi, settings.CICADA_INSTANCE_ID, empreinte_depot, empreinte_lecture,
    )

    try:
        reponse = requests.post(
            f"{url}/instances/adhesion-hub/",
            headers={'X-Instance-Token': jeton_suivi},
            json={
                'instance_id': settings.CICADA_INSTANCE_ID,
                'libelle': settings.CICADA_INSTANCE_LABEL.strip(),
                'url_publique': settings.CICADA_PUBLIC_URL,
                'empreinte_depot': empreinte_depot,
                'empreinte_lecture': empreinte_lecture,
            },
            timeout=DELAI,
        )
    except requests.RequestException as erreur:
        logger.warning("API de suivi injoignable pour la demande d'adhésion : %s", type(erreur).__name__)
        raise ErreurRaccordement('suivi_indisponible', "L'API de suivi est injoignable.")

    if reponse.status_code == 409:
        raise ErreurRaccordement(
            'erreur_inconnue',
            "L'API de suivi refuse la demande : adhésion déjà acceptée, ou "
            "identifiant déjà pris par une autre structure.", 409,
        )
    if reponse.status_code not in (200, 201):
        logger.warning("API de suivi : demande d'adhésion → %s", reponse.status_code)
        raise ErreurRaccordement('suivi_indisponible', "L'API de suivi a refusé ou échoué la demande.")
    try:
        corps = reponse.json()
    except ValueError:
        raise ErreurRaccordement('suivi_indisponible', "Réponse illisible de l'API de suivi.")

    if corps.get('code') != code:
        # Le suivi n'a pas reçu les empreintes envoyées, ou ne calcule pas la
        # même chose : RNF comparerait de vive voix deux codes différents.
        logger.error("Code de vérification divergent entre l'instance et le suivi.")
        raise ErreurRaccordement(
            'code_divergent',
            "Le code de vérification calculé par le suivi ne correspond pas : "
            "la demande n'est pas enregistrée.",
        )

    ligne.jeton_depot_chiffre = chiffrer(depot)
    ligne.jeton_lecture_chiffre = chiffrer(lecture)
    ligne.adhesion_statut = RaccordementHub.STATUT_EN_ATTENTE
    ligne.adhesion_code = code
    ligne.adhesion_instance_id = settings.CICADA_INSTANCE_ID
    ligne.adhesion_demandee_le = timezone.now()
    ligne.adhesion_actualisee_le = ligne.adhesion_demandee_le
    ligne.adhesion_motif = ''
    ligne.hub_url = ''
    ligne.save()
    logger.info("Demande d'adhésion au hub envoyée (instance « %s »).", settings.CICADA_INSTANCE_ID)
    return ligne


# --------------------------------------------------------------------------- #
# Vérification en direct du hub
# --------------------------------------------------------------------------- #

def verifier_hub():
    """
    Interroge le hub : joignable ? cette instance y est-elle reconnue, active ?

    Rien n'est écrit. La réponse ne contient ni jeton ni empreinte : le
    registre du hub n'en rend pas, et on ne recopie que des champs nommés.
    """
    resultat = {
        'hub_joignable': False, 'instance_reconnue': None, 'active': None,
        'derniere_publication': None, 'plans': None, 'contenus': None, 'erreur': None,
    }
    ligne = raccordement()
    url = hub_url(ligne)
    if not url:
        resultat['erreur'] = 'hub_injoignable'
        return resultat

    try:
        sante = requests.get(f"{url}/api/health/", timeout=DELAI)
        resultat['hub_joignable'] = sante.status_code == 200
    except requests.RequestException:
        pass
    if not resultat['hub_joignable']:
        resultat['erreur'] = 'hub_injoignable'
        return resultat

    entetes = {}
    depot, lecture = jeton_depot(ligne), jeton_lecture(ligne)
    if depot:
        entetes['X-Federation-Token'] = depot
    if lecture:
        entetes['X-Hub-Token'] = lecture
    if not entetes:
        # Rien à présenter au hub : pas une erreur, l'instance n'est
        # simplement pas (encore) raccordée — `instance_reconnue` reste nul.
        return resultat

    try:
        reponse = requests.get(f"{url}/api/federation/instances/", headers=entetes, timeout=DELAI)
    except requests.RequestException:
        resultat['erreur'] = 'hub_injoignable'
        return resultat
    if reponse.status_code in (401, 403):
        resultat['instance_reconnue'] = False
        resultat['erreur'] = 'jeton_refuse'
        return resultat
    if reponse.status_code != 200:
        resultat['erreur'] = 'erreur_inconnue'
        return resultat
    try:
        instances = reponse.json().get('instances') or []
    except (ValueError, AttributeError):
        resultat['erreur'] = 'erreur_inconnue'
        return resultat

    moi = next(
        (i for i in instances if isinstance(i, dict)
         and i.get('instance_id') == settings.CICADA_INSTANCE_ID),
        None,
    )
    if moi is None:
        # Le jeton est accepté mais l'instance n'apparaît pas sous son
        # identifiant : le jeton appartient à une autre identité.
        resultat['instance_reconnue'] = False
        resultat['erreur'] = 'jeton_refuse'
        return resultat
    resultat.update({
        'instance_reconnue': True,
        'active': moi.get('active'),
        'derniere_publication': moi.get('derniere_publication'),
        'plans': moi.get('plans_publies'),
        'contenus': moi.get('contenus_publies'),
    })
    return resultat


# --------------------------------------------------------------------------- #
# État complet (contrat avec le frontend)
# --------------------------------------------------------------------------- #

def _date(valeur):
    if valeur is None:
        return None
    from rest_framework.fields import DateTimeField

    return DateTimeField().to_representation(valeur)


def _diagnostic(ligne, configuration, publications):
    """Premier cas qui s'applique, du plus bloquant au plus anodin."""
    statut = ligne.adhesion_statut
    env = configuration['source_jetons'] == SOURCE_ENVIRONNEMENT

    def cas(niveau, cle, **parametres):
        return {'niveau': niveau, 'cle': cle, 'parametres': parametres}

    if not configuration['identite_valide']:
        return cas('erreur', 'identite_manquante')
    if not env and statut == RaccordementHub.STATUT_REFUSEE:
        return cas('erreur', 'adhesion_refusee', motif=ligne.adhesion_motif)
    if not env and statut == RaccordementHub.STATUT_EN_ATTENTE:
        return cas('info', 'adhesion_en_attente', code=ligne.adhesion_code)
    if configuration['source_jetons'] is None:
        return cas('info', 'non_raccorde')
    if not configuration['jeton_depot_defini']:
        # Adhésion acceptée mais jeton indéchiffrable : la SECRET_KEY a changé.
        cause = 'dechiffrement' if (
            not env and ligne.jeton_depot_chiffre
        ) else 'absent'
        return cas('attention', 'jeton_depot_absent', cause=cause)
    if not configuration['partage']:
        return cas('attention', 'partage_inactif')
    significatives = [
        p for p in publications if p.resultat != PublicationHub.RESULTAT_IGNOREE
    ]
    if significatives and significatives[0].resultat == PublicationHub.RESULTAT_ECHEC:
        return cas('erreur', 'derniere_publication_echec', message=significatives[0].message)
    if not significatives:
        return cas('info', 'aucune_publication')
    return cas('ok', 'ok')


def etat(actualiser=True):
    """
    État complet du raccordement, tel que le lit la page de paramètres.

    Une adhésion en attente est d'abord actualisée auprès du suivi : c'est le
    moment où l'administrateur regarde, inutile de lui faire attendre la tâche
    de la demi-heure.
    """
    from apps.system.tracking import instance_token

    from .push import partage_active
    from .relay import relais_actif

    ligne = raccordement()
    erreur_suivi = actualiser_adhesion(ligne) if actualiser else None

    configuration = {
        'instance_id': settings.CICADA_INSTANCE_ID,
        'instance_libelle': settings.CICADA_INSTANCE_LABEL,
        'identite_valide': identite_valide(),
        'hub_url': hub_url(ligne),
        'source_jetons': source_jetons(ligne),
        'jeton_depot_defini': bool(jeton_depot(ligne)),
        'jeton_lecture_defini': bool(jeton_lecture(ligne)),
        'exploration_source': settings.CICADA_EXPLORATION_SOURCE,
        'relais_actif': relais_actif(),
        'publication_auto': settings.CICADA_HUB_PUSH_AUTO,
        'partage': partage_active(),
        'suivi_disponible': bool(instance_token()),
    }
    publications = list(PublicationHub.objects.all()[:PublicationHub.CONSERVATION])

    return {
        'configuration': configuration,
        'adhesion': {
            'statut': ligne.adhesion_statut,
            'code': ligne.adhesion_code,
            'demandee_le': _date(ligne.adhesion_demandee_le),
            'motif': ligne.adhesion_motif,
            'possible': adhesion_possible(ligne),
            'erreur_suivi': erreur_suivi,
        },
        'publications': [
            {
                'date': _date(p.date), 'origine': p.origine, 'resultat': p.resultat,
                'plans': p.plans, 'documents': p.documents, 'depublies': p.depublies,
                'message': p.message,
            }
            for p in publications[:PUBLICATIONS_AFFICHEES]
        ],
        'diagnostic': _diagnostic(ligne, configuration, publications),
    }
