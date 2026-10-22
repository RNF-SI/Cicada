"""Tests de l'installateur web du paquet .deb.

Déroulent run_installation() de bout en bout, Docker et réseau simulés, pour
chaque configuration du formulaire. Une variable supprimée mais encore utilisée
(0.1.56 à 0.1.58 : `frontend_port`, `use_traefik`) ne se voyait qu'au clic sur
« Installer », sur le serveur du client : ici, elle fait échouer le test.

Lancement : packaging/check-installer.sh
"""
import pathlib
import sys

import pytest

INSTALL_DIR = pathlib.Path(__file__).resolve().parents[1] / 'debian/usr/share/cicada/install'
sys.path.insert(0, str(INSTALL_DIR))

import install_service  # noqa: E402

BASE = {
    'admin_email': 'admin@example.org',
    'admin_password': 'Motdepasse123!',
    'admin_nom': 'Admin',
    'admin_prenom': 'Test',
    'domain': 'cicada.example.org',
    'db_password': 'secret',
    'backend_port': '1700',
}

CONFIGURATIONS = {
    'apache_https_base_docker': {'frontend_port': '1717', 'public_access': 'https'},
    'apache_http': {'frontend_port': '8080', 'public_access': 'http'},
    'acces_direct_port': {'frontend_port': '8080', 'public_access': 'port'},
    'traefik': {'use_traefik': 'true', 'acme_email': 'acme@example.org'},
    'base_existante': {
        'frontend_port': '8080', 'db_type': 'existing', 'db_host': '10.0.0.5',
        'db_name': 'cicada', 'db_user': 'cicada_admin',
    },
    'smtp_et_federation': {
        'frontend_port': '8080', 'smtp_enabled': True, 'smtp_host': 'smtp.example.org',
        'smtp_port': '587', 'default_from_email': 'noreply@example.org',
        'federation_enabled': True, 'federation_instance_id': 'test',
        'federation_instance_label': 'Instance de test',
        'federation_hub_url': 'https://hub.example.org',
    },
    'port_frontend_absent': {},
}


@pytest.fixture
def service(tmp_path, monkeypatch):
    """InstallService dont les chemins système pointent dans tmp_path."""
    real_path = pathlib.Path

    def redirected(*parts):
        p = real_path(*parts)
        return tmp_path / p.relative_to('/') if p.is_absolute() else p

    monkeypatch.setattr(install_service, 'Path', redirected)
    monkeypatch.setenv('TRACKING_API_URL', 'https://tracking.example.org/api')
    (tmp_path / 'etc/cicada').mkdir(parents=True)
    (tmp_path / 'etc/cicada/instance_token').write_text('jeton\n')
    (tmp_path / 'var/lib/cicada').mkdir(parents=True)

    svc = install_service.InstallService()
    for step in ('start_docker', 'create_superuser', 'register_instance'):
        monkeypatch.setattr(svc, step, lambda *a, **k: None)
    monkeypatch.setattr(svc, 'test_database', lambda data: [])
    monkeypatch.setattr(svc, 'get_version', lambda: '0.0.0-test')
    return svc


def read_env(tmp_path):
    lines = (tmp_path / 'var/lib/cicada/.env').read_text().splitlines()
    return dict(line.split('=', 1) for line in lines if '=' in line)


@pytest.mark.parametrize('extra', CONFIGURATIONS.values(), ids=CONFIGURATIONS.keys())
def test_installation_complete(service, tmp_path, extra):
    result = service.run_installation({**BASE, **extra})

    assert result.get('success') is True, result
    env = read_env(tmp_path)
    assert env['DJANGO_PORT'] == '1700'
    assert env['FRONTEND_PORT'] == extra.get('frontend_port', '80')
    assert env['SITE_URL'].startswith(('http://', 'https://'))
    assert result['redirect_url'].startswith(('http://', 'https://'))


def test_traefik_publie_en_https(service, tmp_path):
    service.run_installation({**BASE, **CONFIGURATIONS['traefik']})

    env = read_env(tmp_path)
    assert env['TRAEFIK_ENABLED'] == 'true'
    assert env['SITE_URL'] == 'https://cicada.example.org'


def test_apache_publie_sans_le_port_mais_autorise_l_acces_direct(service, tmp_path):
    result = service.run_installation({**BASE, **CONFIGURATIONS['apache_https_base_docker']})

    env = read_env(tmp_path)
    assert env['TRAEFIK_ENABLED'] == 'false'
    assert env['SITE_URL'] == 'https://cicada.example.org'
    assert 'http://cicada.example.org:1717' in env['CORS_ALLOWED_ORIGINS'].split(',')
    assert result['redirect_url'] == 'http://cicada.example.org:1717'


def test_champs_requis_manquants(service):
    result = service.run_installation({'domain': 'cicada.example.org'})

    assert result['success'] is False
    assert result['errors']


# --- PostgreSQL installé sur le serveur CICADA lui-même (hors Docker) ---------

def test_base_locale_jointe_par_host_docker_internal(service, tmp_path):
    result = service.run_installation({
        **BASE, 'frontend_port': '8080', 'db_type': 'existing', 'db_host': 'localhost',
        'db_name': 'cicada', 'db_user': 'cicada_admin',
    })

    assert result['success'] is True, result
    assert read_env(tmp_path)['POSTGRES_HOST'] == 'host.docker.internal'


def test_base_distante_gardee_telle_quelle(service, tmp_path):
    service.run_installation({**BASE, **CONFIGURATIONS['base_existante']})

    assert read_env(tmp_path)['POSTGRES_HOST'] == '10.0.0.5'


@pytest.fixture
def connexions(monkeypatch):
    """psycopg.connect simulé : enregistre l'hôte visé, échoue comme pg_hba.conf."""
    import psycopg
    hotes = []

    def connect(**kwargs):
        hotes.append(kwargs['host'])
        raise psycopg.OperationalError(
            f'connection failed: FATAL: no pg_hba.conf entry for host "{kwargs["host"]}"')

    monkeypatch.setattr(psycopg, 'connect', connect)
    return hotes


def test_test_de_connexion_locale_passe_par_le_pont_docker(monkeypatch, connexions):
    svc = install_service.InstallService()
    monkeypatch.setattr(svc, 'docker_gateway', lambda: '172.17.0.1')

    checks = svc.test_database({'db_host': 'localhost', 'db_name': 'cicada',
                                'db_user': 'cicada_admin', 'db_password': 'x'})

    assert connexions == ['172.17.0.1']
    assert '--docker-local' in checks[0]['detail']


def test_liste_d_adresses_refusee(connexions):
    checks = install_service.InstallService().test_database({
        'db_host': '162.19.89.37, 172.17.0.1, 2001:41d0:306:2c25::',
        'db_name': 'cicada', 'db_user': 'cicada_admin', 'db_password': 'x'})

    assert checks[0]['label'] == 'Indiquez une seule adresse'
    assert connexions == []


def test_commande_de_preparation_locale():
    svc = install_service.InstallService()

    assert svc.is_local_db('localhost')
    assert svc.client_ip_for('127.0.0.1') == svc.DOCKER_NETWORKS
    assert not svc.is_local_db('10.0.0.5')


def test_conteneurs_de_l_application_joignent_l_hote():
    import yaml
    compose = yaml.safe_load((INSTALL_DIR.parent / 'docker-compose.yml').read_text())

    for service_name in ('web', 'celery-worker', 'celery-beat'):
        assert 'host.docker.internal:host-gateway' in compose['services'][service_name]['extra_hosts']


def test_la_mise_a_jour_relance_l_installateur():
    """Sans relance, une mise à jour laisse tourner l'installateur de la version
    précédente : le formulaire ignorait les corrections du paquet installé."""
    postinst = (INSTALL_DIR.parents[3] / 'DEBIAN/postinst').read_text()

    assert 'systemctl try-restart cicada-installer.service' in postinst
