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


def test_le_planificateur_connait_l_identite_de_l_instance():
    """#847 — le créneau de publication de nuit est calculé par beat, au
    chargement des réglages. Sans l'identifiant, beat voit « local » et toutes
    les instances publient à la même heure."""
    services = _services()
    for nom in SERVICES_DJANGO:
        assert 'CICADA_INSTANCE_ID' in _environnement(services[nom]), nom


# --------------------------------------------------------------------------- #
# #846 — journaux, bornes, arrêt
# --------------------------------------------------------------------------- #

COMPOSES_LIVRES = [
    RACINE / 'packaging/debian/usr/share/cicada/docker-compose.yml',
    RACINE / 'packaging/debian/usr/share/cicada/docker-compose.db.yml',
    RACINE / 'packaging/debian/usr/share/cicada/docker-compose.traefik.yml',
    RACINE / 'docker-compose.hub.prod.yml',
]


def _services_definis(fichier):
    """Services qu'un fichier crée (une image), pas ceux qu'il complète."""
    services = yaml.safe_load(fichier.read_text())['services']
    return {nom: s for nom, s in services.items() if 'image' in s or 'build' in s}


def test_chaque_conteneur_livre_a_des_journaux_bornes():
    """Le pilote json-file par défaut n'a pas de taille maximale : un
    conteneur qui boucle remplit le disque, la base s'arrête."""
    for fichier in COMPOSES_LIVRES:
        for nom, service in _services_definis(fichier).items():
            journaux = service.get('logging') or {}
            options = journaux.get('options') or {}
            assert options.get('max-size') and options.get('max-file'), f'{fichier.name} : {nom}'


def test_le_worker_celery_est_borne():
    commande = ' '.join(_services()['celery-worker']['command'])
    assert '--concurrency=' in commande
    assert '--max-tasks-per-child=' in commande
    assert '--max-memory-per-child=' in commande


def _secondes(duree):
    duree = str(duree)
    return int(duree[:-1]) * (60 if duree.endswith('m') else 1)


def test_une_tache_en_cours_a_le_temps_de_finir_a_l_arret():
    """`docker compose stop` envoie SIGKILL après stop_grace_period (10 s par
    défaut) : une tâche acquittée dès son démarrage n'est pas rejouée."""
    services = _services()
    assert _secondes(services['celery-worker'].get('stop_grace_period', '10s')) >= 60
    assert _secondes(services['web'].get('stop_grace_period', '10s')) >= 30
    db = _services_definis(RACINE / 'packaging/debian/usr/share/cicada/docker-compose.db.yml')['db']
    assert _secondes(db.get('stop_grace_period', '10s')) >= 30


def test_gunicorn_recycle_ses_processus():
    dockerfile = (RACINE / 'backend/Dockerfile.prod').read_text()
    assert '--max-requests' in dockerfile and '--max-requests-jitter' in dockerfile


def test_les_fichiers_de_journaux_tournent_sur_l_hote():
    """Plusieurs processus (gunicorn, Celery) écrivent les mêmes fichiers :
    la rotation se fait sur l'hôte (logrotate), pas dans chaque processus."""
    regle = RACINE / 'packaging/debian/etc/logrotate.d/cicada'
    texte = regle.read_text()
    assert '/var/log/cicada/django.log' in texte and '/var/log/cicada/audit.log' in texte
    assert 'copytruncate' in texte
    assert '/etc/logrotate.d/cicada' in (RACINE / 'packaging/debian/DEBIAN/conffiles').read_text()
    assert 'logrotate' in (RACINE / 'packaging/debian/DEBIAN/control').read_text()
