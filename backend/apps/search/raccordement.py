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
toute façon.

## Confirmation par code envoyé par e-mail

RNF prend contact avec l'administrateur déclaré dans la demande, puis lui
envoie **par e-mail** un code de confirmation tiré au hasard par le suivi.
L'administrateur le saisit dans `Administration > Paramètres` : l'instance le
relaie au suivi, qui le vérifie et enrôle alors l'instance sur le hub. Le code
ne transite que dans cette requête — il n'est **jamais** stocké ni journalisé
ici : une base ou un journal copiés ne doivent pas permettre de le rejouer.

Aucun jeton ni aucune empreinte ne sort de ce module dans une réponse d'API ou
une ligne de journal.
"""

import base64
import hashlib
import json
import logging
import re
import secrets

import requests
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.utils import timezone
from django.utils.dateparse import parse_datetime

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

    def __init__(self, cle, message, statut_http=400, extra=None):
        super().__init__(message)
        self.cle = cle
        self.message = message
        self.statut_http = statut_http
        #: Champs complémentaires rendus tels quels (ex. `essais_restants`).
        self.extra = extra or {}

    def corps(self):
        return {'erreur': self.cle, 'detail': self.message, **self.extra}


# --------------------------------------------------------------------------- #
# Formules partagées avec l'API de suivi — à garder À L'IDENTIQUE
# --------------------------------------------------------------------------- #

def empreinte(jeton):
    """Empreinte SHA-256 d'un jeton — même formule que le hub."""
    return hashlib.sha256(jeton.encode('utf-8')).hexdigest()


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


#: Statuts pendant lesquels la décision appartient au suivi : l'instance doit
#: aller relire où en est sa demande.
STATUTS_A_ACTUALISER = (RaccordementHub.STATUT_EN_ATTENTE, RaccordementHub.STATUT_CODE_ENVOYE)


def _date_suivi(valeur):
    """Date ISO 8601 reçue du suivi, ou ``None`` si absente ou illisible."""
    if not isinstance(valeur, str):
        return None
    try:
        return parse_datetime(valeur)
    except ValueError:
        return None


def actualiser_adhesion(ligne=None):
    """
    Relit auprès du suivi l'état d'une adhésion en attente ou dont le code de
    confirmation a été envoyé.

    Renvoie une clé d'erreur, ou ``None`` si l'actualisation a réussi (ou n'avait
    pas lieu d'être). Ne lève jamais : une page d'administration doit pouvoir
    s'afficher même si le suivi est injoignable.
    """
    ligne = ligne or raccordement()
    if ligne.adhesion_statut not in STATUTS_A_ACTUALISER:
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
        RaccordementHub.STATUT_EN_ATTENTE, RaccordementHub.STATUT_CODE_ENVOYE,
        RaccordementHub.STATUT_ACCEPTEE, RaccordementHub.STATUT_REFUSEE,
    ):
        return 'suivi_indisponible'
    ancien = ligne.adhesion_statut
    ligne.adhesion_statut = statut
    ligne.adhesion_motif = corps.get('motif_refus') or ''
    ligne.adhesion_code_expire_le = (
        _date_suivi(corps.get('code_expire_le'))
        if statut == RaccordementHub.STATUT_CODE_ENVOYE else None
    )
    if statut == RaccordementHub.STATUT_ACCEPTEE and corps.get('hub_url'):
        ligne.hub_url = corps['hub_url'].rstrip('/')
    ligne.adhesion_actualisee_le = timezone.now()
    ligne.save()
    if statut != ancien:
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


#: Bornes des champs de contact — celles du modèle, et de quoi refuser un
#: message démesuré avant de le faire voyager.
LONGUEURS_CONTACT = {
    'contact_nom': 200, 'contact_email': 254, 'contact_telephone': 50, 'message': 5000,
}


def valider_contact(donnees):
    """
    Contact déclaré dans la demande d'adhésion, nettoyé.

    Nom et e-mail sont requis : c'est à cette personne que RNF téléphone, puis
    envoie le code de confirmation. Lève `contact_invalide` sinon.
    """
    if not isinstance(donnees, dict):
        donnees = {}
    contact = {}
    for champ, longueur in LONGUEURS_CONTACT.items():
        valeur = donnees.get(champ)
        if valeur is None:
            valeur = ''
        if not isinstance(valeur, str) or len(valeur.strip()) > longueur:
            raise ErreurRaccordement('contact_invalide', f"Champ « {champ} » invalide.")
        contact[champ] = valeur.strip()
    if not contact['contact_nom']:
        raise ErreurRaccordement('contact_invalide', "Le nom du contact est requis.")
    try:
        validate_email(contact['contact_email'])
    except ValidationError:
        raise ErreurRaccordement('contact_invalide', "L'adresse e-mail du contact est invalide.")
    return contact


def demander_adhesion(donnees=None):
    """
    Tire deux jetons, envoie leurs empreintes au suivi et enregistre la demande.

    `donnees` porte le contact de l'administrateur (`contact_nom`,
    `contact_email`, `contact_telephone`, `message`), transmis au suivi.

    Les jetons ne sont enregistrés qu'**après** la réponse favorable du suivi :
    une demande qui échoue laisse l'état précédent intact. Un suivi qui aurait enregistré
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
    contact = valider_contact(donnees)
    url, jeton_suivi = _suivi()

    depot, lecture = nouveau_jeton(), nouveau_jeton()
    empreinte_depot, empreinte_lecture = empreinte(depot), empreinte(lecture)

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
                **contact,
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
    ligne.jeton_depot_chiffre = chiffrer(depot)
    ligne.jeton_lecture_chiffre = chiffrer(lecture)
    ligne.adhesion_statut = RaccordementHub.STATUT_EN_ATTENTE
    ligne.adhesion_instance_id = settings.CICADA_INSTANCE_ID
    ligne.adhesion_demandee_le = timezone.now()
    ligne.adhesion_actualisee_le = ligne.adhesion_demandee_le
    ligne.adhesion_motif = ''
    ligne.adhesion_contact_nom = contact['contact_nom']
    ligne.adhesion_contact_email = contact['contact_email']
    ligne.adhesion_code_expire_le = None
    ligne.hub_url = ''
    ligne.retrait_en_attente = False
    ligne.save()
    # Demander l'adhésion, c'est consentir au partage : rejoindre l'exploration
    # nationale n'a de sens qu'en y versant ses plans (réciprocité). Le
    # formulaire le dit avant l'envoi ; la case des paramètres en est le reflet,
    # et la décocher reste possible à tout moment. Aucune publication n'est
    # lancée ici : tant que l'adhésion n'est pas acceptée, il n'y a pas de jeton.
    from apps.core.models import SiteConfiguration

    configuration = SiteConfiguration.get_instance()
    if not configuration.federation_partage:
        configuration.federation_partage = True
        configuration.save(update_fields=['federation_partage', 'updated_at'])
    logger.info("Demande d'adhésion au hub envoyée (instance « %s »).", settings.CICADA_INSTANCE_ID)
    return ligne


#: Erreurs de confirmation que le suivi renvoie et que l'instance relaie telles
#: quelles (clé et statut HTTP) — le contrat avec l'interface est le même.
ERREURS_CONFIRMATION = {
    'code_invalide': 400, 'code_expire': 400, 'trop_d_essais': 400,
    'pas_de_code': 409, 'hub_injoignable': 502,
}


def confirmer_adhesion(code):
    """
    Relaie au suivi le code de confirmation saisi par l'administrateur.

    Code juste ⇒ le suivi enrôle l'instance sur le hub et répond `acceptee` :
    les jetons tirés à la demande deviennent effectifs. Le code n'est ni
    conservé ni journalisé — seuls le statut HTTP et la clé d'erreur le sont.
    """
    ligne = raccordement()
    if ligne.adhesion_statut == RaccordementHub.STATUT_ACCEPTEE:
        raise ErreurRaccordement('deja_acceptee', "L'adhésion est déjà acceptée.", 409)
    if ligne.adhesion_statut not in STATUTS_A_ACTUALISER:
        raise ErreurRaccordement(
            'pas_de_code', "Aucune demande d'adhésion en cours de confirmation.", 409,
        )
    if not isinstance(code, str) or not code.strip() or len(code) > 50:
        raise ErreurRaccordement('code_invalide', "Saisissez le code reçu par e-mail.")
    url, jeton_suivi = _suivi()

    try:
        reponse = requests.post(
            f"{url}/instances/adhesion-hub/confirmation/",
            headers={'X-Instance-Token': jeton_suivi},
            json={'code': code.strip()},
            timeout=DELAI,
        )
    except requests.RequestException as erreur:
        logger.warning("API de suivi injoignable pour la confirmation d'adhésion : %s", type(erreur).__name__)
        raise ErreurRaccordement('suivi_indisponible', "L'API de suivi est injoignable.")
    try:
        corps = reponse.json()
    except ValueError:
        corps = {}
    if not isinstance(corps, dict):
        corps = {}

    if reponse.status_code == 200 and corps.get('statut') == RaccordementHub.STATUT_ACCEPTEE:
        ligne.adhesion_statut = RaccordementHub.STATUT_ACCEPTEE
        ligne.adhesion_motif = ''
        ligne.adhesion_code_expire_le = None
        if corps.get('hub_url'):
            ligne.hub_url = corps['hub_url'].rstrip('/')
        ligne.adhesion_actualisee_le = timezone.now()
        ligne.save()
        logger.info("Adhésion au hub confirmée par code (instance « %s »).", settings.CICADA_INSTANCE_ID)
        return ligne

    if reponse.status_code == 404:
        cle = 'pas_de_code'
    else:
        cle = corps.get('erreur')
    if cle not in ERREURS_CONFIRMATION:
        logger.warning("API de suivi : confirmation d'adhésion → %s", reponse.status_code)
        raise ErreurRaccordement('suivi_indisponible', "L'API de suivi a refusé ou échoué la confirmation.")

    logger.info("Confirmation d'adhésion refusée par le suivi : %s", cle)
    if cle == 'trop_d_essais':
        # Le suivi a invalidé le code et repassé la demande en attente : RNF
        # doit en renvoyer un. Autant l'afficher sans attendre l'actualisation.
        ligne.adhesion_statut = RaccordementHub.STATUT_EN_ATTENTE
        ligne.adhesion_code_expire_le = None
        ligne.adhesion_actualisee_le = timezone.now()
        ligne.save()
    extra = {}
    if cle == 'code_invalide' and isinstance(corps.get('essais_restants'), int):
        extra['essais_restants'] = corps['essais_restants']
    messages = {
        'code_invalide': "Code de confirmation incorrect.",
        'code_expire': "Ce code de confirmation a expiré : demandez-en un nouveau à RNF.",
        'trop_d_essais': "Trop d'essais : ce code est invalidé, RNF doit en envoyer un nouveau.",
        'pas_de_code': "Aucun code de confirmation n'est en cours de validité pour cette instance.",
        'hub_injoignable': "Code accepté, mais l'enrôlement sur le hub a échoué : réessayez plus tard.",
    }
    raise ErreurRaccordement(cle, messages[cle], ERREURS_CONFIRMATION[cle], extra)


def contacter_rnf(utilisateur, donnees):
    """
    Envoie à RNF, via le suivi, un message de l'administrateur connecté.

    Le nom et l'adresse de réponse viennent du **compte connecté**, pas du
    corps de la requête : RNF répond à quelqu'un dont l'instance garantit
    l'adresse, et la page ne sert pas de relais d'e-mails au nom de n'importe qui.
    """
    if not isinstance(donnees, dict):
        donnees = {}
    sujet, message = donnees.get('sujet'), donnees.get('message')
    if not (isinstance(sujet, str) and sujet.strip() and len(sujet) <= 200
            and isinstance(message, str) and message.strip() and len(message) <= 5000):
        raise ErreurRaccordement('contact_invalide', "Le sujet et le message sont requis.")
    url, jeton_suivi = _suivi()
    try:
        reponse = requests.post(
            f"{url}/instances/contact/",
            headers={'X-Instance-Token': jeton_suivi},
            json={
                'nom': utilisateur.get_full_name() or utilisateur.email,
                'email': utilisateur.email,
                'sujet': sujet.strip(),
                'message': message.strip(),
            },
            timeout=DELAI,
        )
    except requests.RequestException as erreur:
        logger.warning("API de suivi injoignable pour un message à RNF : %s", type(erreur).__name__)
        raise ErreurRaccordement('suivi_indisponible', "L'API de suivi est injoignable.")
    if reponse.status_code not in (200, 201, 202):
        logger.warning("API de suivi : message à RNF → %s", reponse.status_code)
        raise ErreurRaccordement(
            'suivi_indisponible', "L'API de suivi a refusé ou échoué l'envoi du message.",
            429 if reponse.status_code == 429 else 400,
        )


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
# Consentement au partage : retrait et republication
# --------------------------------------------------------------------------- #

#: Le retrait est déclenché depuis la page des paramètres : l'administrateur
#: attend. Il ne fait que deux appels légers (ouvrir un lot, le basculer).
DELAI_RETRAIT = 30


def retirer_du_hub(origine=PublicationHub.ORIGINE_MANUELLE, hub=None, jeton=None):
    """
    Retire du hub **tous** les plans publiés par cette instance.

    Un lot est ouvert puis basculé sans qu'aucun plan n'y soit déposé : le hub
    purge alors tout ce qui n'a pas été revu, c'est-à-dire tout. Aucun endpoint
    de suppression n'est nécessaire — le mécanisme d'état s'en charge, et il est
    déjà éprouvé par chaque publication.

    C'est aussi ce qui retire l'**accès** à l'exploration nationale : le hub ne
    sert que les instances qui y ont des plans publiés (réciprocité,
    `PeutLire`). Une fois la purge faite, c'est donc le hub — pas l'instance,
    que quiconque l'administre pourrait reconfigurer — qui refuse la lecture.

    Renvoie le nombre de plans retirés. Lève `ErreurRaccordement` si le hub est
    absent, injoignable ou refuse : l'appelant décide s'il faut réessayer. Le
    succès est consigné dans l'historique (`RESULTAT_RETRAIT`) et efface le
    drapeau `retrait_en_attente` : un retrait réussi, d'où qu'il vienne,
    satisfait celui qui attendait.
    """
    ligne = raccordement()
    url = (hub or hub_url(ligne)).rstrip('/')
    jeton = jeton or jeton_depot(ligne)
    if not url or not jeton:
        raise ErreurRaccordement(
            'non_raccorde',
            "Hub ou jeton de dépôt manquant : renseignez CICADA_HUB_URL et "
            "CICADA_HUB_PUSH_TOKEN, ou faites accepter l'adhésion de l'instance.",
        )

    from .push import FORMAT_VERSION

    entetes = {'X-Federation-Token': jeton, 'Content-Type': 'application/json'}

    def appel(methode, chemin, corps=None):
        try:
            reponse = requests.request(
                methode, f"{url}{chemin}", headers=entetes,
                data=json.dumps(corps) if corps is not None else None,
                timeout=DELAI_RETRAIT,
            )
        except requests.RequestException as erreur:
            raise ErreurRaccordement(
                'hub_injoignable', f"Hub injoignable ({type(erreur).__name__}).", 502,
            )
        if reponse.status_code >= 400:
            raise ErreurRaccordement(
                'hub_injoignable',
                f"{methode} {chemin} → {reponse.status_code} : {reponse.text[:300]}", 502,
            )
        return reponse.json() if reponse.content else {}

    lot = appel('POST', '/api/federation/lots/', {'format_version': FORMAT_VERSION})['lot_id']
    resultat = appel('POST', f'/api/federation/lots/{lot}/bascule/')
    purges = resultat.get('plans_purges', 0) or 0

    if ligne.retrait_en_attente:
        ligne.retrait_en_attente = False
        ligne.save()
    PublicationHub.enregistrer(origine, PublicationHub.RESULTAT_RETRAIT, depublies=purges)
    logger.info(
        "Plans de l'instance « %s » retirés du hub : %s plan(s) dépublié(s).",
        settings.CICADA_INSTANCE_ID, purges,
    )
    return purges


def retrait_possible(ligne=None):
    """Y a-t-il un hub et un jeton de dépôt — donc quelque chose à retirer ?"""
    ligne = ligne or raccordement()
    return bool(hub_url(ligne) and jeton_depot(ligne))


def partage_retire():
    """
    Le consentement au partage vient d'être retiré : retirer les plans du hub.

    Le consentement retiré est honoré **même si le hub est injoignable** : la
    case reste décochée (cette fonction ne lève jamais, la mise à jour des
    paramètres n'échoue donc pas), et le drapeau `retrait_en_attente` fait
    relancer le retrait chaque heure (`relancer_retrait_hub`). Le premier échec
    est consigné dans l'historique ; les relances suivantes ne le sont qu'en
    cas de succès, pour ne pas noyer le tableau de bord sous une ligne par heure.

    Renvoie ``True`` si le retrait a abouti (ou n'avait pas lieu d'être).
    """
    ligne = raccordement()
    if not retrait_possible(ligne):
        # Jamais raccordée : rien n'a pu être publié, rien à retirer.
        return True
    try:
        retirer_du_hub(PublicationHub.ORIGINE_MANUELLE)
        return True
    except ErreurRaccordement as erreur:
        logger.warning("Retrait du hub impossible, relancé plus tard : %s", erreur.message)
        ligne = raccordement()
        ligne.retrait_en_attente = True
        ligne.save()
        PublicationHub.enregistrer(
            PublicationHub.ORIGINE_MANUELLE, PublicationHub.RESULTAT_ECHEC,
            message=f"Retrait : {erreur.message}",
        )
        return False


def partage_accorde():
    """
    Le consentement au partage vient d'être (re)donné : republier sans attendre.

    Sans cela, une structure qui recoche la case resterait privée de
    l'exploration nationale jusqu'à la nuit suivante — le hub ne la sert qu'une
    fois ses plans republiés. Un retrait encore en attente devient sans objet :
    la publication remplace de toute façon l'état complet sur le hub.

    La publication part **en arrière-plan** et seulement après la validation de
    la transaction : la tâche relit le consentement en base. Si le broker est
    indisponible, la publication de nuit prendra le relais.
    """
    from django.db import transaction

    ligne = raccordement()
    if ligne.retrait_en_attente:
        ligne.retrait_en_attente = False
        ligne.save()
    if not retrait_possible(ligne):
        return

    def lancer():
        from .tasks import publier_apres_consentement

        try:
            publier_apres_consentement.delay()
        except Exception:  # noqa: BLE001 — broker indisponible : la nuit rattrapera
            logger.warning(
                "Publication après consentement non planifiée (broker indisponible) "
                "— la publication de nuit prendra le relais."
            )

    transaction.on_commit(lancer)


def consentement_modifie(avant, apres):
    """Point d'entrée unique d'une modification de `federation_partage`."""
    if avant and not apres:
        partage_retire()
    elif apres and not avant:
        partage_accorde()


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
    if not env and statut == RaccordementHub.STATUT_CODE_ENVOYE:
        return cas('info', 'adhesion_code_envoye', expire_le=_date(ligne.adhesion_code_expire_le))
    if not env and statut == RaccordementHub.STATUT_EN_ATTENTE:
        return cas('info', 'adhesion_en_attente')
    if configuration['source_jetons'] is None:
        return cas('info', 'non_raccorde')
    if not configuration['jeton_depot_defini']:
        # Adhésion acceptée mais jeton indéchiffrable : la SECRET_KEY a changé.
        cause = 'dechiffrement' if (
            not env and ligne.jeton_depot_chiffre
        ) else 'absent'
        return cas('attention', 'jeton_depot_absent', cause=cause)
    if ligne.retrait_en_attente:
        # Le consentement est retiré mais les plans sont encore sur le hub :
        # l'instance garde, d'ici le prochain essai, l'accès qu'elle a refusé.
        return cas('attention', 'retrait_en_attente')
    if not configuration['partage']:
        return cas('attention', 'partage_inactif')
    significatives = [
        p for p in publications if p.resultat != PublicationHub.RESULTAT_IGNOREE
    ]
    if significatives and significatives[0].resultat == PublicationHub.RESULTAT_ECHEC:
        return cas('erreur', 'derniere_publication_echec', message=significatives[0].message)
    if not significatives or significatives[0].resultat == PublicationHub.RESULTAT_RETRAIT:
        # Partage recoché, republication pas encore faite : rien sur le hub.
        return cas('info', 'aucune_publication')
    return cas('ok', 'ok')


def etat(actualiser=True):
    """
    État complet du raccordement, tel que le lit la page de paramètres.

    Une adhésion en attente (ou dont le code a été envoyé) est d'abord actualisée auprès du suivi : c'est le
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
            'demandee_le': _date(ligne.adhesion_demandee_le),
            'motif': ligne.adhesion_motif,
            'code_expire_le': _date(ligne.adhesion_code_expire_le),
            'contact_email': ligne.adhesion_contact_email,
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
