"""
Integration tests for Validations API.
Tests the /api/validations/ endpoints.
"""
import pytest
from rest_framework.test import APIClient
from rest_framework import status

from apps.notifications.models import ValidationRequest
from tests.factories.users import (
    RoleFactory, SuperAdminFactory, AdminOrganismeFactory, OrganismeFactory
)


@pytest.fixture
def api_client():
    """Return an unauthenticated API client."""
    return APIClient()


@pytest.fixture
def authenticated_client(db):
    """Return an authenticated API client with a regular user."""
    user = RoleFactory()
    client = APIClient()
    client.force_authenticate(user=user)
    return client, user


@pytest.fixture
def admin_client(db):
    """Return an authenticated API client with an admin user."""
    admin = SuperAdminFactory()
    client = APIClient()
    client.force_authenticate(user=admin)
    return client, admin


@pytest.fixture
def admin_og_client(db):
    """Return an authenticated API client with an admin organisme."""
    organisme = OrganismeFactory()
    admin_og = AdminOrganismeFactory(id_organisme=organisme)
    client = APIClient()
    client.force_authenticate(user=admin_og)
    return client, admin_og


# =============================================================================
# TYPES ENDPOINT TESTS
# =============================================================================

@pytest.mark.django_db
@pytest.mark.integration
class TestValidationTypesEndpoint:
    """Tests for GET /api/validations/types/ endpoint."""

    def test_types_requires_authentication(self, api_client):
        """Test types endpoint requires authentication."""
        response = api_client.get('/api/validations/types/')

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_types_returns_request_types(self, authenticated_client):
        """Test types endpoint returns request_types list."""
        client, user = authenticated_client

        response = client.get('/api/validations/types/')

        assert response.status_code == status.HTTP_200_OK
        assert 'request_types' in response.data
        assert isinstance(response.data['request_types'], list)
        assert len(response.data['request_types']) > 0

    def test_types_returns_statuses(self, authenticated_client):
        """Test types endpoint returns statuses list."""
        client, user = authenticated_client

        response = client.get('/api/validations/types/')

        assert response.status_code == status.HTTP_200_OK
        assert 'statuses' in response.data
        assert isinstance(response.data['statuses'], list)
        assert len(response.data['statuses']) > 0

    def test_types_format_is_correct(self, authenticated_client):
        """Test types endpoint returns correct format with value and label."""
        client, user = authenticated_client

        response = client.get('/api/validations/types/')

        assert response.status_code == status.HTTP_200_OK

        # Check request_types format
        for item in response.data['request_types']:
            assert 'value' in item
            assert 'label' in item
            assert isinstance(item['value'], str)
            assert isinstance(item['label'], str)

        # Check statuses format
        for item in response.data['statuses']:
            assert 'value' in item
            assert 'label' in item
            assert isinstance(item['value'], str)
            assert isinstance(item['label'], str)

    def test_types_contains_expected_request_types(self, authenticated_client):
        """Test types endpoint contains all expected request types."""
        client, user = authenticated_client

        response = client.get('/api/validations/types/')

        assert response.status_code == status.HTTP_200_OK

        # Get all values from response
        values = [item['value'] for item in response.data['request_types']]

        # Check expected types are present
        expected_types = [
            'user_registration',
            'site_creation',
            'site_access',
            'plan_access',
            'module_access',
            'admin_deactivation',
            'admin_promotion',
            'admin_demotion',
            'referent_validation',
            'site_org_link',
            'site_org_unlink',
            'invite_org_to_site',
            'invite_user_to_site',
        ]

        for expected_type in expected_types:
            assert expected_type in values, f"Missing request type: {expected_type}"

    def test_types_contains_expected_statuses(self, authenticated_client):
        """Test types endpoint contains all expected statuses."""
        client, user = authenticated_client

        response = client.get('/api/validations/types/')

        assert response.status_code == status.HTTP_200_OK

        # Get all values from response
        values = [item['value'] for item in response.data['statuses']]

        # Check expected statuses are present
        expected_statuses = ['pending', 'approved', 'rejected', 'cancelled', 'expired']

        for expected_status in expected_statuses:
            assert expected_status in values, f"Missing status: {expected_status}"

    def test_types_matches_model_definition(self, authenticated_client):
        """Test types endpoint matches ValidationRequest model definition."""
        client, user = authenticated_client

        response = client.get('/api/validations/types/')

        assert response.status_code == status.HTTP_200_OK

        # Compare with model definition
        model_request_types = dict(ValidationRequest.REQUEST_TYPES)
        model_statuses = dict(ValidationRequest.STATUS_CHOICES)

        response_request_types = {
            item['value']: item['label']
            for item in response.data['request_types']
        }
        response_statuses = {
            item['value']: item['label']
            for item in response.data['statuses']
        }

        # Check counts match
        assert len(response_request_types) == len(model_request_types)
        assert len(response_statuses) == len(model_statuses)

        # Check all model types are in response
        for value, label in model_request_types.items():
            assert value in response_request_types
            assert response_request_types[value] == str(label)

        for value, label in model_statuses.items():
            assert value in response_statuses
            assert response_statuses[value] == str(label)

    def test_types_accessible_to_regular_user(self, authenticated_client):
        """Test types endpoint is accessible to regular users."""
        client, user = authenticated_client

        response = client.get('/api/validations/types/')

        assert response.status_code == status.HTTP_200_OK

    def test_types_accessible_to_admin_og(self, admin_og_client):
        """Test types endpoint is accessible to admin organisme."""
        client, admin_og = admin_og_client

        response = client.get('/api/validations/types/')

        assert response.status_code == status.HTTP_200_OK

    def test_types_accessible_to_super_admin(self, admin_client):
        """Test types endpoint is accessible to super admin."""
        client, admin = admin_client

        response = client.get('/api/validations/types/')

        assert response.status_code == status.HTTP_200_OK
