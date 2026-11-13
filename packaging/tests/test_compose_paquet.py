"""Le compose livré par le paquet : ce que chaque conteneur reçoit.

Ces défauts ne se voient qu'en production (les tests du backend tournent avec
les réglages de développement) : on les vérifie donc sur le fichier livré.
"""
import importlib.util
from pathlib import Path

import yaml

RACINE = Path(__file__).resolve().parents[2]
COMPOSE = RACINE / 'packaging/debian/usr/share/cicada/docker-compose.yml'
SERVICES_DJANGO = ('web', 'celery-worker', 'celery-beat')


def _services():
    return yaml.safe_load(COMPOSE.read_text())['services']


def _environnement(service):
    env = service.get('environment') or []
    if isinstance(env, dict):
        return {k: str(v) for k, v in env.items()}
    return dict(ligne.split('=', 1) for ligne in env if '=' in ligne)


def _url_cache():
    spec = importlib.util.spec_from_file_location(
        'redis_urls', RACINE / 'backend/config/redis_urls.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.url_cache


def test_le_cache_de_chaque_conteneur_porte_le_mot_de_passe_de_redis():
    url_cache = _url_cache()
    services = _services()
    assert 'requirepass' in ' '.join(services['redis']['command']
                                     if isinstance(services['redis']['command'], list)
                                     else [services['redis']['command']])
    for nom in SERVICES_DJANGO:
        assert '${REDIS_PASSWORD}' in url_cache(_environnement(services[nom])), nom
