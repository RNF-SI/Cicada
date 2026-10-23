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


# --- Connexion UsersHub par la base (#764) --------------------------------------

USERSHUB_BASE = {
    'frontend_port': '8080', 'auth_provider': 'geonature', 'geonature_auth_source': 'base',
    'geonature_auth_libelle': 'RNF', 'geonature_auth_code_application': 'CICADA',
    'usershub_db_host': '10.0.20.21', 'usershub_db_port': '5432', 'usershub_db_name': 'geonature2db',
    'usershub_db_user': 'cicada_usershub', 'usershub_db_password': 'mdp-lecture',
}


def test_usershub_par_la_base_ecrit_sa_configuration(service, tmp_path):
    result = service.run_installation({**BASE, **USERSHUB_BASE})

    assert result['success'] is True, result
    env = read_env(tmp_path)
    assert env['AUTH_PROVIDER'] == 'geonature'
    assert env['GEONATURE_AUTH_SOURCE'] == 'base'
    assert env['GEONATURE_AUTH_CODE_APPLICATION'] == 'CICADA'
    assert env['USERSHUB_DB_HOST'] == '10.0.20.21'
    assert env['USERSHUB_DB_PASSWORD'] == 'mdp-lecture'
    # Base distante : les empreintes des mots de passe passent sur le réseau.
    assert env['USERSHUB_DB_SSLMODE'] == 'require'
    assert env['USERSHUB_DB_SSLROOTCERT'] == ''


def test_usershub_sur_ce_serveur_joint_par_le_pont_docker(service, tmp_path):
    service.run_installation({**BASE, **USERSHUB_BASE, 'usershub_db_host': 'localhost'})

    env = read_env(tmp_path)
    assert env['USERSHUB_DB_HOST'] == 'host.docker.internal'
    assert env['USERSHUB_DB_SSLMODE'] == 'prefer'


def test_usershub_chiffrement_choisi_dans_le_formulaire(service, tmp_path):
    service.run_installation({**BASE, **USERSHUB_BASE, 'usershub_db_sslmode': 'verify-full'})
    env = read_env(tmp_path)
    assert env['USERSHUB_DB_SSLMODE'] == 'verify-full'
    assert env['USERSHUB_DB_SSLROOTCERT'] == '/etc/cicada/usershub/ca.crt'

    service.run_installation({**BASE, **USERSHUB_BASE, 'usershub_db_sslmode': 'prefer'})
    assert read_env(tmp_path)['USERSHUB_DB_SSLMODE'] == 'prefer'


def test_certificat_usershub_monte_dans_web():
    import yaml
    compose = yaml.safe_load((INSTALL_DIR.parent / 'docker-compose.yml').read_text())
    web = compose['services']['web']

    assert '/etc/cicada/usershub:/etc/cicada/usershub:ro' in web['volumes']
    assert 'USERSHUB_DB_SSLMODE=${USERSHUB_DB_SSLMODE:-prefer}' in web['environment']
    assert 'mkdir -p "$CONFIG_DIR/usershub"' in (INSTALL_DIR.parents[3] / 'DEBIAN/postinst').read_text()


def test_usershub_par_la_base_champs_requis(service):
    result = service.run_installation({**BASE, **USERSHUB_BASE, 'usershub_db_password': '',
                                       'geonature_auth_code_application': ''})

    assert result['success'] is False
    assert any('mot de passe' in e for e in result['errors'])
    assert any("code de l'application" in e for e in result['errors'])


def test_usershub_par_l_api_garde_l_ancien_reglage(service, tmp_path):
    service.run_installation({**BASE, 'frontend_port': '8080', 'auth_provider': 'geonature',
                              'geonature_auth_source': 'api', 'geonature_auth_url': 'https://gn.test/api',
                              'geonature_auth_id_application': '18', 'geonature_auth_libelle': 'RNF'})

    env = read_env(tmp_path)
    assert env['GEONATURE_AUTH_SOURCE'] == 'api'
    assert env['GEONATURE_AUTH_URL'] == 'https://gn.test/api'
    assert env['USERSHUB_DB_HOST'] == ''


def test_mode_local_n_ecrit_aucune_base_usershub(service, tmp_path):
    service.run_installation({**BASE, **USERSHUB_BASE, 'auth_provider': 'local'})

    env = read_env(tmp_path)
    assert env['AUTH_PROVIDER'] == 'local'
    assert env['USERSHUB_DB_PASSWORD'] == ''


# --- Compte de lecture UsersHub (#764) ------------------------------------------

LECTURE_SCRIPT = INSTALL_DIR.parents[2] / 'bin/cicada-usershub-lecture'
BACKEND_USERSHUB = INSTALL_DIR.parents[5] / 'backend/apps/authentication/providers/usershub_base.py'


def colonnes_accordees():
    """{table: {colonnes}} des GRANT SELECT (…) ON %I.<table> du script."""
    import re
    texte = LECTURE_SCRIPT.read_text()
    accord = {}
    for cols, table in re.findall(r"GRANT SELECT \(([^)]*)\) ON %I\.(\w+)", texte.replace("'\n              '", '')
                                  .replace("' '", '').replace("'\n", '')):
        accord[table] = {c.strip() for c in cols.replace("'", '').split(',')}
    return accord


def test_le_compte_de_lecture_couvre_les_requetes_du_backend():
    """Une colonne ajoutée à une requête de connexion sans être accordée par le
    script = toutes les connexions en 502, sur le serveur du client."""
    import ast
    import re
    accord = colonnes_accordees()
    assert set(accord) == {'t_roles', 'cor_roles', 'cor_role_app_profil', 't_applications', 'bib_organismes'}
    module = ast.parse(BACKEND_USERSHUB.read_text())
    requetes = [n.value.value for n in module.body if isinstance(n, ast.Assign)
                and isinstance(n.value, ast.Constant) and isinstance(n.value.value, str) and '{s}.' in n.value.value]
    assert len(requetes) == 4  # COMPTE, DROIT, ACCES, ORGANISME
    mots_sql = {'select', 'from', 'where', 'and', 'or', 'is', 'not', 'true', 'false', 'exists', 'join', 'on',
                'in', 'any', 'lower', 's'}
    tables = set(accord)
    toutes = set().union(*accord.values())
    for requete in requetes:
        sans_params = re.sub(r'%\(\w+\)s|%s', '', requete)
        lues = {m for m in re.findall(r'[a-z_]+', sans_params.lower())} - mots_sql - tables
        lues = {m for m in lues if len(m) > 1}  # alias p, a
        assert lues <= toutes, f"colonnes non accordées par cicada-usershub-lecture : {lues - toutes}"
        for table in re.findall(r'\{s\}\.(\w+)', requete):
            assert table in tables


def test_le_test_du_formulaire_lit_les_memes_colonnes_que_le_script():
    import re
    accord = colonnes_accordees()
    source = (INSTALL_DIR / 'install_service.py').read_text()
    for cols, table in re.findall(r'SELECT ([a-z_, "\n]+?) ?"?\s*"?FROM utilisateurs\.(\w+) WHERE false',
                                  source.replace('"\n                           "', '').replace('"\n                        "', '')):
        assert {c.strip() for c in cols.split(',')} == accord[table], table


def test_le_script_du_compte_de_lecture_est_servi_par_l_installateur(monkeypatch):
    import app
    monkeypatch.setattr(app.install_service, 'USERSHUB_LECTURE_SCRIPT', LECTURE_SCRIPT)
    reponse = app.app.test_client().get('/usershub-lecture.sh')
    assert reponse.status_code == 200
    assert 'GRANT SELECT (id_role, groupe' in reponse.get_data(as_text=True)
    assert LECTURE_SCRIPT.stat().st_mode & 0o111, 'script non exécutable'
