"""
Tests for System API endpoints (/api/system/).
Tests version info and trigger-update (super_admin only).
"""
import json
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

from rest_framework.test import APIClient
from rest_framework import status

from config.version import __version__
from tests.factories.users import SuperAdminFactory, AdminOrganismeFactory, RoleFactory


@pytest.fixture
def api_client():
    return APIClient()


# =============================================================================
# Résolution de la version (#646)
# =============================================================================

@pytest.mark.unit
class TestVersionResolution:
    """La version affichée doit être celle de l'instance, jamais "0.0.0".

    Le contexte de build du backend est ``./backend`` : version.txt, à la racine
    du dépôt, n'entre pas dans l'image de production. D'où l'injection par
    variable d'environnement, prioritaire sur le fichier.
    """

    def test_env_var_wins_over_file(self, monkeypatch):
        from config.version import _read_version

        monkeypatch.setenv('CICADA_APP_VERSION', '9.9.9')
        assert _read_version() == '9.9.9'

    def test_empty_env_var_falls_back_to_file(self, monkeypatch):
        """Env vide (cas du dev) : on retombe sur version.txt."""
        from config import version as version_module

        monkeypatch.setenv('CICADA_APP_VERSION', '   ')
        monkeypatch.setattr(version_module.Path, 'exists', lambda self: True)
        monkeypatch.setattr(version_module.Path, 'read_text', lambda self: '1.2.3\n')
        assert version_module._read_version() == '1.2.3'

    def test_no_source_returns_zero(self, monkeypatch):
        from config import version as version_module

        monkeypatch.setenv('CICADA_APP_VERSION', '')
        monkeypatch.setattr(version_module.Path, 'exists', lambda self: False)
        assert version_module._read_version() == '0.0.0'


# =============================================================================
# GET /api/system/app-version/  (#646)
# =============================================================================

@pytest.mark.django_db
@pytest.mark.integration
class TestSystemAppVersionEndpoint:
    """Version applicative affichée dans l'administration (#646).

    Contrairement à /api/system/version/ (réservée au super admin car elle porte
    aussi l'état de mise à jour et son déclenchement), cet endpoint ne renvoie
    que la version : le pied de la sidebar d'administration est visible par le
    référent et l'admin organisme.
    """

    def test_unauthenticated_returns_401(self, api_client):
        response = api_client.get('/api/system/app-version/')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_regular_user_returns_version(self, api_client):
        api_client.force_authenticate(user=RoleFactory())
        response = api_client.get('/api/system/app-version/')
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {'version': __version__}

    def test_admin_og_returns_version(self, api_client):
        api_client.force_authenticate(user=AdminOrganismeFactory())
        response = api_client.get('/api/system/app-version/')
        assert response.status_code == status.HTTP_200_OK
        assert response.json()['version'] == __version__

    def test_super_admin_returns_version(self, api_client):
        api_client.force_authenticate(user=SuperAdminFactory())
        response = api_client.get('/api/system/app-version/')
        assert response.status_code == status.HTTP_200_OK
        assert response.json()['version'] == __version__


# =============================================================================
# GET /api/system/version/
# =============================================================================

@pytest.mark.django_db
@pytest.mark.integration
class TestSystemVersionEndpoint:
    """Tests for GET /api/system/version/."""

    def test_unauthenticated_returns_401(self, api_client):
        response = api_client.get('/api/system/version/')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_regular_user_returns_403(self, api_client):
        user = RoleFactory()
        api_client.force_authenticate(user=user)
        response = api_client.get('/api/system/version/')
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_admin_og_returns_403(self, api_client):
        admin = AdminOrganismeFactory()
        api_client.force_authenticate(user=admin)
        response = api_client.get('/api/system/version/')
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_super_admin_returns_version_no_update_file(self, api_client):
        """When no update file exists, returns current version with no update."""
        admin = SuperAdminFactory()
        api_client.force_authenticate(user=admin)
        with patch.object(Path, 'exists', return_value=False):
            response = api_client.get('/api/system/version/')
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data['current_version'] == __version__
        assert data['update_available'] is False
        assert data['latest_version'] is None
        assert data['last_check'] is None

    def test_super_admin_returns_update_info_from_file(self, api_client):
        """When update file exists, returns its content."""
        admin = SuperAdminFactory()
        api_client.force_authenticate(user=admin)
        update_data = {
            'current_version': '0.0.1',
            'update_available': True,
            'latest_version': '0.2.0',
            'last_check': '2026-03-16T10:00:00Z',
        }
        with patch.object(Path, 'exists', return_value=True), \
             patch.object(Path, 'read_text', return_value=json.dumps(update_data)):
            response = api_client.get('/api/system/version/')
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data['update_available'] is True
        assert data['latest_version'] == '0.2.0'
        assert data['last_check'] == '2026-03-16T10:00:00Z'

    def test_installed_version_prevails_over_heartbeat_file(self, api_client):
        """Juste après une mise à jour, le fichier du heartbeat dit encore
        l'ancienne version : c'est la version installée qui compte, et la
        mise à jour n'est plus proposée si l'annoncée n'est pas plus récente."""
        admin = SuperAdminFactory()
        api_client.force_authenticate(user=admin)
        stale = {
            'current_version': '0.0.1',
            'update_available': True,
            'latest_version': __version__,
            'last_check': '2026-03-16T10:00:00Z',
        }
        with patch.object(Path, 'exists', return_value=True), \
             patch.object(Path, 'read_text', return_value=json.dumps(stale)):
            response = api_client.get('/api/system/version/')
        data = response.json()
        assert data['current_version'] == __version__
        assert data['update_available'] is False
        assert data['update_pending'] is True      # déclencheur présent (exists patché)
        assert data['last_update'] == stale         # dernier résultat lu tel quel

    def test_no_files_means_nothing_pending(self, api_client):
        admin = SuperAdminFactory()
        api_client.force_authenticate(user=admin)
        with patch.object(Path, 'exists', return_value=False):
            data = api_client.get('/api/system/version/').json()
        assert data['update_pending'] is False
        assert data['check_pending'] is False
        assert data['last_check_error'] is None
        assert data['last_update'] is None

    def test_check_error_from_heartbeat_file(self, api_client):
        """L'échec de la dernière interrogation de l'API de suivi est rendu tel quel."""
        api_client.force_authenticate(user=SuperAdminFactory())
        announced = {'latest_version': None, 'last_check_error': 'HTTP 401'}
        with patch.object(Path, 'exists', return_value=True), \
             patch.object(Path, 'read_text', return_value=json.dumps(announced)):
            data = api_client.get('/api/system/version/').json()
        assert data['last_check_error'] == 'HTTP 401'
        assert data['check_pending'] is True

    def test_corrupt_update_file_returns_defaults(self, api_client):
        """When update file is corrupt JSON, returns safe defaults."""
        admin = SuperAdminFactory()
        api_client.force_authenticate(user=admin)
        with patch.object(Path, 'exists', return_value=True), \
             patch.object(Path, 'read_text', return_value='not valid json'):
            response = api_client.get('/api/system/version/')
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data['current_version'] == __version__
        assert data['update_available'] is False


    def test_echec_avec_retour_arriere_et_derniere_sauvegarde(self, api_client, tmp_path, monkeypatch):
        """#796 — la page dit ce qui s'est passé (cause, retour arrière fait ou
        non) et quand date la dernière sauvegarde, écrits par le serveur."""
        from apps.system import api_views
        resultat = {
            'success': False, 'version': '0.1.70', 'timestamp': '2026-11-06T10:05:00+01:00',
            'error': "L'application ne démarre pas : ProgrammingError — retour à la version 0.1.69 effectué",
            'statut': 'echec_retour_fait', 'depart': '0.1.69', 'cible': '0.1.70', 'retour_arriere': True,
            'sauvegarde': '20261106-100000-avant-maj-0.1.69-vers-0.1.70', 'commande': None,
            'journal': '/var/log/cicada/maj-20261106-100400-cicada_prod_web.log',
        }
        sauvegardes = {'nombre': 3, 'dossier': '/var/backups/cicada', 'derniere': {
            'nom': '20261106-100000-avant-maj-0.1.69-vers-0.1.70', 'date': '2026-11-06T10:00:40+01:00',
            'raison': 'avant-maj-0.1.69-vers-0.1.70', 'version': '0.1.69', 'taille': 45000000}}
        (tmp_path / 'update_result.json').write_text(json.dumps(resultat))
        (tmp_path / 'backups.json').write_text(json.dumps(sauvegardes))
        for nom, fichier in (('UPDATE_RESULT_FILE', 'update_result.json'), ('BACKUPS_FILE', 'backups.json'),
                             ('UPDATE_AVAILABLE_FILE', 'absent.json'), ('UPDATE_TRIGGER_FILE', 'absent.json'),
                             ('CHECK_TRIGGER_FILE', 'absent.json')):
            monkeypatch.setattr(api_views, nom, tmp_path / fichier)
        api_client.force_authenticate(user=SuperAdminFactory())

        data = api_client.get('/api/system/version/').json()

        assert data['last_update']['statut'] == 'echec_retour_fait'
        assert data['last_update']['retour_arriere'] is True
        assert data['last_backup'] == sauvegardes

    def test_sans_sauvegarde_connue(self, api_client, tmp_path, monkeypatch):
        from apps.system import api_views
        monkeypatch.setattr(api_views, 'BACKUPS_FILE', tmp_path / 'absent.json')
        api_client.force_authenticate(user=SuperAdminFactory())
        assert api_client.get('/api/system/version/').json()['last_backup'] is None


# =============================================================================
# POST /api/system/check-update/
# =============================================================================

@pytest.mark.django_db
@pytest.mark.integration
class TestSystemCheckUpdateEndpoint:
    """Bouton « Vérifier les mises à jour » : dépose le déclencheur du heartbeat."""

    def test_unauthenticated_returns_401(self, api_client):
        response = api_client.post('/api/system/check-update/')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_admin_og_returns_403(self, api_client):
        api_client.force_authenticate(user=AdminOrganismeFactory())
        response = api_client.post('/api/system/check-update/')
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_super_admin_writes_check_trigger(self, api_client):
        from apps.system.api_views import CHECK_TRIGGER_FILE

        admin = SuperAdminFactory()
        api_client.force_authenticate(user=admin)
        written = {}

        def mock_write(self, content):
            written[str(self)] = json.loads(content)

        with patch.object(Path, 'write_text', autospec=True, side_effect=mock_write):
            response = api_client.post('/api/system/check-update/')
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {'success': True}
        assert written == {str(CHECK_TRIGGER_FILE): {'requested_by': admin.email}}

    def test_write_error_returns_500(self, api_client):
        api_client.force_authenticate(user=SuperAdminFactory())
        with patch.object(Path, 'write_text', side_effect=OSError('Permission denied')):
            response = api_client.post('/api/system/check-update/')
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert 'error' in response.json()


# =============================================================================
# POST /api/system/trigger-update/
# =============================================================================

@pytest.mark.django_db
@pytest.mark.integration
class TestSystemTriggerUpdateEndpoint:
    """Tests for POST /api/system/trigger-update/."""

    def test_unauthenticated_returns_401(self, api_client):
        response = api_client.post('/api/system/trigger-update/', {'version': '0.2.0'}, format='json')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_regular_user_returns_403(self, api_client):
        user = RoleFactory()
        api_client.force_authenticate(user=user)
        response = api_client.post('/api/system/trigger-update/', {'version': '0.2.0'}, format='json')
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_missing_version_returns_400(self, api_client):
        admin = SuperAdminFactory()
        api_client.force_authenticate(user=admin)
        response = api_client.post('/api/system/trigger-update/', {}, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'error' in response.json()

    def test_super_admin_triggers_update(self, api_client):
        """Super admin can trigger an update, writes trigger file."""
        admin = SuperAdminFactory()
        api_client.force_authenticate(user=admin)
        written_content = {}

        def mock_write(content):
            written_content['data'] = json.loads(content)

        with patch.object(Path, 'write_text', side_effect=mock_write):
            response = api_client.post('/api/system/trigger-update/', {'version': '0.2.0'}, format='json')
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data['success'] is True
        assert '0.2.0' in data['message']
        assert written_content['data']['version'] == '0.2.0'
        assert written_content['data']['requested_by'] == admin.email

    def test_refuse_si_une_mise_a_jour_est_deja_programmee(self, api_client, tmp_path):
        """Second onglet, page rechargée pendant la coupure : pas de deuxième
        demande, qui relancerait l'updater juste après la première."""
        admin = SuperAdminFactory()
        api_client.force_authenticate(user=admin)
        declencheur = tmp_path / 'update_trigger.json'
        declencheur.write_text('{"version": "0.2.0", "requested_by": "x"}')
        with patch('apps.system.api_views.UPDATE_TRIGGER_FILE', declencheur):
            response = api_client.post('/api/system/trigger-update/', {'version': '0.2.0'}, format='json')
        assert response.status_code == status.HTTP_409_CONFLICT
        assert 'déjà programmée' in response.json()['error']
        assert json.loads(declencheur.read_text())['requested_by'] == 'x'

    def test_refuse_la_version_deja_en_service(self, api_client, tmp_path):
        """Demander la version qui tourne remplaçait le compte rendu de la vraie
        mise à jour par « déjà à jour » (constaté sur le staging, 0.1.69 → 0.1.72)."""
        admin = SuperAdminFactory()
        api_client.force_authenticate(user=admin)
        declencheur = tmp_path / 'update_trigger.json'
        with patch('apps.system.api_views.UPDATE_TRIGGER_FILE', declencheur), \
                patch('apps.system.api_views.__version__', '0.2.0'):
            response = api_client.post('/api/system/trigger-update/', {'version': '0.2.0'}, format='json')
        assert response.status_code == status.HTTP_409_CONFLICT
        assert 'déjà en service' in response.json()['error']
        assert not declencheur.exists()

    def test_trigger_update_file_write_error(self, api_client):
        """When trigger file cannot be written, returns 500."""
        admin = SuperAdminFactory()
        api_client.force_authenticate(user=admin)
        with patch.object(Path, 'write_text', side_effect=OSError('Permission denied')):
            response = api_client.post('/api/system/trigger-update/', {'version': '0.2.0'}, format='json')
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert 'error' in response.json()
