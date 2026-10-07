"""
Adhésion d'une instance CICADA au hub d'exploration fédérée (#696).

Une structure demande l'adhésion depuis son instance. RNF prend contact avec son
administrateur, puis lui envoie depuis l'admin de l'API de suivi un **code de
confirmation** par e-mail ; l'administrateur le saisit sur son instance, et un
code juste enrôle l'instance sur le hub. RNF a décidé en envoyant le code : il n'y
a pas d'acceptation sans code.

L'API de suivi est le seul détenteur du jeton d'administration du hub : c'est
elle qui enrôle l'instance, avec les **empreintes** des jetons que l'instance a
tirés elle-même. Le jeton du hub ne voyage donc jamais — ni par l'API de suivi,
ni par un humain.

Le code est tiré au hasard, jamais dérivé de données que l'instance connaît :
une instance usurpatrice pourrait sinon le recalculer sans attendre l'e-mail.
"""
import hashlib
import logging
import re
import secrets
from datetime import timedelta

import requests
from django.conf import settings
from django.core.mail import EmailMessage
from django.utils import timezone

logger = logging.getLogger(__name__)

# Même expression que l'installeur et le hub : l'identifiant devient la clé de
# l'instance dans toutes les tables du hub, il doit donc y être accepté tel quel.
REGEX_IDENTIFIANT = re.compile(r'^[a-z0-9][a-z0-9-]{0,49}$')
REGEX_EMPREINTE = re.compile(r'^[0-9a-f]{64}$')

# L'admin attend la réponse du hub pendant que la page se charge : mieux vaut un
# échec franc et rapide qu'une page figée.
DELAI_HUB = 10


def empreinte(jeton: str) -> str:
    """SHA-256 hexadécimal du jeton — même formule que le hub, qui ne stocke qu'elle."""
    return hashlib.sha256(jeton.encode('utf-8')).hexdigest()


# --- Code de confirmation --------------------------------------------------

# Sans 0/O, 1/I/L : le code est recopié à la main depuis un e-mail.
ALPHABET_CODE = 'ABCDEFGHJKMNPQRSTUVWXYZ23456789'
LONGUEUR_CODE = 8
VALIDITE_CODE = timedelta(days=7)
# Au-delà, le code est invalidé et RNF doit en renvoyer un : 5 essais sur 31^8
# combinaisons ne laissent aucune chance à qui devine.
ESSAIS_MAX = 5


def tirer_code() -> str:
    """Code aléatoire présenté « ABCD-EFGH »."""
    brut = ''.join(secrets.choice(ALPHABET_CODE) for _ in range(LONGUEUR_CODE))
    return f"{brut[:4]}-{brut[4:]}"


def normaliser_code(code: str) -> str:
    """Insensible à la casse, aux espaces et aux tirets : on compare ce qui a été tapé."""
    return re.sub(r'[\s-]+', '', str(code or '')).upper()


def empreinte_code(code: str) -> str:
    """Seule forme du code conservée par le suivi."""
    return empreinte(normaliser_code(code))


def code_correct(adhesion, code: str) -> bool:
    saisi = normaliser_code(code)
    if not saisi or not adhesion.code_empreinte:
        return False
    return secrets.compare_digest(empreinte(saisi), adhesion.code_empreinte)


# --- E-mails ----------------------------------------------------------------

def _envoyer(sujet, corps, destinataires, reply_to=None):
    EmailMessage(subject=sujet, body=corps, from_email=settings.DEFAULT_FROM_EMAIL,
                 to=destinataires, reply_to=reply_to).send(fail_silently=False)


def lien_admin(adhesion) -> str:
    base = (getattr(settings, 'ADMIN_BASE_URL', '') or '').rstrip('/')
    return f"{base}/admin/instances/adhesionhub/{adhesion.pk}/change/"


def _lignes_contact(adhesion):
    lignes = [f"Contact : {adhesion.contact_nom} <{adhesion.contact_email}>"]
    if adhesion.contact_telephone:
        lignes.append(f"Téléphone : {adhesion.contact_telephone}")
    return lignes


def notifier_nouvelle_demande(adhesion):
    """Prévient RNF et accuse réception au demandeur.

    Un échec d'envoi est journalisé sans faire échouer la demande : elle est
    enregistrée et visible dans l'admin, ce qui est l'essentiel.
    """
    lignes = [
        "Une instance CICADA demande à rejoindre l'exploration nationale.",
        "",
        f"Structure : {adhesion.libelle}",
        f"Identifiant demandé : {adhesion.instance_id_demande}",
        f"URL publique : {adhesion.url_publique or '(non renseignée)'}",
        *_lignes_contact(adhesion),
    ]
    if adhesion.message:
        lignes += ["", "Message :", adhesion.message]
    lignes += [
        "",
        f"Fiche de la demande : {lien_admin(adhesion)}",
        "",
        "Avant d'envoyer le code de confirmation, prenez contact avec l'administrateur et vérifiez "
        "que l'adresse d'envoi du code appartient bien à la structure.",
    ]
    try:
        _envoyer(f"[CICADA] Nouvelle demande d'adhésion au hub — {adhesion.libelle}",
                 '\n'.join(lignes), [settings.RNF_CONTACT_EMAIL], reply_to=[adhesion.contact_email])
    except Exception:  # noqa: BLE001 — SMTP, réseau : tout échec se vaut ici
        logger.exception("Adhésion %s : e-mail à RNF non envoyé", adhesion.pk)

    accuse = '\n'.join([
        f"Bonjour {adhesion.contact_nom},",
        "",
        f"Réserves Naturelles de France a bien reçu la demande de « {adhesion.libelle} » "
        f"(identifiant « {adhesion.instance_id_demande} ») pour rejoindre l'exploration nationale "
        "des plans de gestion CICADA.",
        "",
        "Nous allons prendre contact avec vous. Une fois la demande vérifiée, vous recevrez par "
        "e-mail un code de confirmation, à saisir dans CICADA : Administration > Paramètres > "
        "Exploration fédérée.",
        "",
        "Si vous n'êtes pas à l'origine de cette demande, signalez-le en répondant à ce message.",
        "",
        "L'équipe CICADA — Réserves Naturelles de France",
    ])
    try:
        _envoyer("[CICADA] Votre demande d'adhésion à l'exploration nationale", accuse,
                 [adhesion.contact_email], reply_to=[settings.RNF_CONTACT_EMAIL])
    except Exception:  # noqa: BLE001
        logger.exception("Adhésion %s : accusé de réception non envoyé", adhesion.pk)


def envoyer_code(adhesion, code, expire_le):
    """Envoie le code à `email_confirmation`. Laisse remonter l'échec : l'admin doit le voir."""
    ou = "Administration > Paramètres > Exploration fédérée"
    if adhesion.url_publique:
        ou += f" ({adhesion.url_publique.rstrip('/')}/administration/parametres)"
    corps = '\n'.join([
        "Bonjour,",
        "",
        f"Réserves Naturelles de France a validé la demande de « {adhesion.libelle} » pour rejoindre "
        "l'exploration nationale des plans de gestion CICADA.",
        "",
        f"Votre code de confirmation : {code}",
        "",
        f"Il est valable 7 jours (jusqu'au {timezone.localtime(expire_le):%d/%m/%Y}). Saisissez-le dans CICADA : {ou}.",
        f"Après {ESSAIS_MAX} saisies erronées, il est invalidé et un nouveau code doit vous être envoyé.",
        "",
        "Si vous n'êtes pas à l'origine de cette demande, ne saisissez pas ce code et répondez à ce message.",
        "",
        "L'équipe CICADA — Réserves Naturelles de France",
    ])
    _envoyer("[CICADA] Votre code de confirmation pour l'exploration nationale", corps,
             [adhesion.email_confirmation], reply_to=[settings.RNF_CONTACT_EMAIL])


def envoyer_message_contact(instance, adhesion, nom, email, sujet, message):
    """Message libre d'un administrateur d'instance à RNF. Laisse remonter l'échec."""
    structure = (adhesion.libelle if adhesion else '') or instance.structure_name or 'instance CICADA'
    identifiant = adhesion.instance_id_demande if adhesion else "(aucune demande d'adhésion)"
    lignes = [
        f"Message de {nom} <{email}>",
        f"Structure : {structure}",
        f"Identifiant d'instance : {identifiant}",
        f"URL publique : {(adhesion.url_publique if adhesion else '') or '(inconnue)'}",
        f"Instance (jeton de suivi) : {str(instance.token)[:8]}…",
        f"Version : {instance.version}",
        "",
        f"Sujet : {sujet}",
        "",
        message,
    ]
    _envoyer(f"[CICADA] Message de {structure} — {sujet}", '\n'.join(lignes),
             [settings.RNF_CONTACT_EMAIL], reply_to=[email])


# --- Enrôlement sur le hub --------------------------------------------------

class EchecEnrolement(Exception):
    """L'enrôlement sur le hub n'a pas abouti ; le message est destiné à l'admin RNF."""


def enroler_sur_hub(adhesion) -> str:
    """Enrôle l'instance sur le hub avec ses empreintes ; renvoie l'URL du hub.

    Le hub répond 201 (créée) ou 200 (déjà enrôlée avec exactement ces empreintes :
    un nouvel essai après une coupure ne doit pas échouer). Tout le reste est un
    échec, et la demande garde son statut : on ne marque jamais « acceptée » une
    instance que le hub ne connaît pas. Appelée par la confirmation par code.

    Le jeton d'administration n'apparaît dans aucun message d'erreur.
    """
    hub_url = (getattr(settings, 'HUB_URL', '') or '').rstrip('/')
    jeton = getattr(settings, 'HUB_ADMIN_TOKEN', '') or ''
    if not hub_url or not jeton:
        raise EchecEnrolement(
            "HUB_URL et HUB_ADMIN_TOKEN doivent être renseignés dans le .env de l'API de suivi "
            "(puis redémarrer le service) avant de pouvoir enrôler une instance."
        )

    try:
        reponse = requests.post(
            f"{hub_url}/api/federation/enrolements/",
            json={
                'instance_id': adhesion.instance_id_demande,
                'libelle': adhesion.libelle,
                'url_publique': adhesion.url_publique,
                'empreinte_depot': adhesion.empreinte_depot,
                'empreinte_lecture': adhesion.empreinte_lecture,
            },
            headers={'X-Hub-Admin-Token': jeton},
            timeout=DELAI_HUB,
        )
    except requests.RequestException as exc:
        raise EchecEnrolement(f"Hub injoignable ({hub_url}) : {exc.__class__.__name__}.") from exc

    if reponse.status_code in (200, 201):
        return hub_url

    try:
        detail = reponse.json().get('detail') or reponse.json()
    except ValueError:
        detail = reponse.text[:200]
    if reponse.status_code == 409:
        raise EchecEnrolement(
            f"L'identifiant « {adhesion.instance_id_demande} » est déjà enrôlé sur le hub avec "
            f"d'autres jetons. À trancher sur le hub (enroler_instance). Détail : {detail}"
        )
    if reponse.status_code == 403:
        raise EchecEnrolement(
            "Le hub refuse le jeton d'administration (HUB_ADMIN_TOKEN absent du hub, ou différent "
            "de celui de l'API de suivi)."
        )
    raise EchecEnrolement(f"Le hub a répondu {reponse.status_code} : {detail}")
