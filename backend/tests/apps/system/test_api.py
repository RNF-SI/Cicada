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

    def test_trigger_update_file_write_error(self, api_client):
        """When trigger file cannot be written, returns 500."""
        admin = SuperAdminFactory()
        api_client.force_authenticate(user=admin)
        with patch.object(Path, 'write_text', side_effect=OSError('Permission denied')):
            response = api_client.post('/api/system/trigger-update/', {'version': '0.2.0'}, format='json')
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert 'error' in response.json()
