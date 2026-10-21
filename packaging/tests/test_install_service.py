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
