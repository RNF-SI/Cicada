"""
Adhésion d'une instance CICADA au hub d'exploration fédérée (#696).

Une structure demande l'adhésion depuis son instance ; un admin RNF l'accepte ou
la refuse ici, dans l'admin de l'API de suivi. L'API de suivi est le seul
détenteur du jeton d'administration du hub : c'est elle qui enrôle l'instance,
avec les **empreintes** des jetons que l'instance a tirés elle-même. Le jeton du
hub ne voyage donc jamais — ni par l'API de suivi, ni par un humain.

La vérification de l'identité de la structure avant acceptation sera définie
plus tard (#697).
"""
import hashlib
import re

import requests
from django.conf import settings

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


class EchecEnrolement(Exception):
    """L'enrôlement sur le hub n'a pas abouti ; le message est destiné à l'admin RNF."""


def enroler_sur_hub(adhesion) -> str:
    """Enrôle l'instance sur le hub avec ses empreintes ; renvoie l'URL du hub.

    Le hub répond 201 (créée) ou 200 (déjà enrôlée avec exactement ces empreintes :
    un nouvel essai après une coupure ne doit pas échouer). Tout le reste est un
    échec, et la demande reste en attente : on ne marque jamais « acceptée » une
    instance que le hub ne connaît pas.

    Le jeton d'administration n'apparaît dans aucun message d'erreur.
    """
    hub_url = (getattr(settings, 'HUB_URL', '') or '').rstrip('/')
    jeton = getattr(settings, 'HUB_ADMIN_TOKEN', '') or ''
    if not hub_url or not jeton:
        raise EchecEnrolement(
            "HUB_URL et HUB_ADMIN_TOKEN doivent être renseignés dans le .env de l'API de suivi "
            "(puis redémarrer le service) avant de pouvoir accepter une adhésion."
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
