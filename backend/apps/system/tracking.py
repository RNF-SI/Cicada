"""
Accès à l'API de suivi RNF (TrackingCicada) depuis l'application.

Deux informations suffisent pour parler au suivi : son URL, et le jeton qui
identifie cette instance (`X-Instance-Token`). Elles vivent sur l'**hôte** —
`/etc/cicada/cicada.conf` (fixé à la construction du paquet) et
`/etc/cicada/instance_token` (tiré par le postinst) —, alors que l'application
tourne dans un conteneur. Le compose packagé transmet donc l'URL par variable
d'environnement et monte le jeton en lecture seule ; avant #696 ni l'un ni
l'autre n'atteignaient le conteneur, et tout appel au suivi échouait en silence.

Ce module centralise la résolution : la page système (RGPD) et l'adhésion au
hub d'exploration (#696) lisent au même endroit, dans le même ordre.
"""

import configparser
import os
from pathlib import Path

#: URL par défaut de l'API de suivi hébergée par RNF.
DEFAULT_TRACKING_API_URL = 'https://tracking.cicada.reserves-naturelles.org/api'

#: Fichiers de l'hôte, montés dans le conteneur par le compose packagé.
CONF_FILE = Path('/etc/cicada/cicada.conf')
TOKEN_FILE = Path('/etc/cicada/instance_token')


def tracking_api_url():
    """
    URL de l'API de suivi, sans barre finale.

    Ordre : variable d'environnement `TRACKING_API_URL` (écrite dans le `.env`
    par l'installeur et transmise au conteneur, ou réglée en dev), puis
    `/etc/cicada/cicada.conf` (cas d'un processus lancé sur l'hôte), puis la
    valeur par défaut. Une variable *définie mais vide* — ce que produit
    `${TRACKING_API_URL:-}` dans le compose — compte comme absente.
    """
    url = (os.environ.get('TRACKING_API_URL') or '').strip()
    if not url and CONF_FILE.exists():
        config = configparser.ConfigParser()
        try:
            config.read(CONF_FILE)
            url = (config.get('CICADA', 'TRACKING_API_URL', fallback='') or '').strip()
        except configparser.Error:
            url = ''
    return (url or DEFAULT_TRACKING_API_URL).rstrip('/')


def instance_token():
    """
    Jeton de cette instance auprès du suivi, ou ``None`` s'il est introuvable.

    `CICADA_TRACKING_TOKEN` d'abord, pour le développement (aucun fichier
    d'hôte en local) ; sinon le fichier monté. ``None`` plutôt qu'une
    exception : l'absence de jeton est un état à diagnostiquer et à afficher
    (instance non installée par le paquet, montage manquant), pas une panne.
    """
    jeton = (os.environ.get('CICADA_TRACKING_TOKEN') or '').strip()
    if jeton:
        return jeton
    try:
        jeton = TOKEN_FILE.read_text().strip()
    except OSError:
        return None
    return jeton or None
