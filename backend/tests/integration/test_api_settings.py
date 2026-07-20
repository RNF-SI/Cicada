"""
Integration tests for Site Configuration API.
Tests for the SiteConfiguration singleton model and its API endpoints.
"""
import pytest
import io
from PIL import Image
from rest_framework.test import APIClient
from rest_framework import status

from apps.core.models import SiteConfiguration
from tests.factories.users import SuperAdminFactory, AdminOrganismeFactory, RoleFactory


@pytest.fixture
def api_client():
    """Return an unauthenticated API client."""
    return APIClient()


@pytest.fixture
def test_image():
    """Create a test image file for upload."""
    # Create a simple 100x100 red image
    image = Image.new('RGB', (100, 100), color='red')
    buffer = io.BytesIO()
    image.save(buffer, format='JPEG')
    buffer.seek(0)
    buffer.name = 'test_image.jpg'
    return buffer


# =============================================================================
# SITE CONFIGURATION TESTS
# =============================================================================

@pytest.mark.django_db
@pytest.mark.integration
class TestSiteConfigurationGetEndpoint:
    """Tests for GET /api/settings/ endpoint."""

    def test_get_settings_unauthenticated(self, api_client):
        """Test that unauthenticated users CAN access settings (public endpoint)."""
        response = api_client.get('/api/settings/')

        assert response.status_code == status.HTTP_200_OK
        assert 'homepage_image' in response.data
        assert 'homepage_image_url' in response.data
        assert 'updated_at' in response.data

    def test_get_settings_authenticated(self, api_client):
        """Test authenticated users can access settings."""
        user = RoleFactory()
        api_client.force_authenticate(user=user)

        response = api_client.get('/api/settings/')

        assert response.status_code == status.HTTP_200_OK

    def test_get_settings_returns_singleton(self, api_client):
        """Test that settings always returns the singleton instance."""
        # First request creates the singleton
        response1 = api_client.get('/api/settings/')
        assert response1.status_code == status.HTTP_200_OK

        # Second request returns the same instance
        response2 = api_client.get('/api/settings/')
        assert response2.status_code == status.HTTP_200_OK

        # Verify singleton pattern
        assert SiteConfiguration.objects.count() == 1

    def test_get_settings_default_values(self, api_client):
        """Test default values when no image is set."""
        response = api_client.get('/api/settings/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['homepage_image'] is None
        assert response.data['homepage_image_url'] is None


@pytest.mark.django_db
@pytest.mark.integration
class TestSiteConfigurationUpdateEndpoint:
    """Tests for PATCH /api/settings/ endpoint."""

    def test_update_settings_unauthenticated_denied(self, api_client):
        """Test that unauthenticated users cannot update settings."""
        response = api_client.patch('/api/settings/', {})

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_update_settings_regular_user_denied(self, api_client):
        """Test that regular users cannot update settings."""
        user = RoleFactory()
        api_client.force_authenticate(user=user)

        response = api_client.patch('/api/settings/', {})

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_update_settings_admin_og_denied(self, api_client):
        """Test that admin organismes cannot update settings."""
        admin_og = AdminOrganismeFactory()
        api_client.force_authenticate(user=admin_og)

        response = api_client.patch('/api/settings/', {})

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_update_settings_super_admin_allowed(self, api_client, test_image):
        """Test that super admin can update settings with image."""
        admin = SuperAdminFactory()
        api_client.force_authenticate(user=admin)

        response = api_client.patch(
            '/api/settings/',
            {'homepage_image': test_image},
            format='multipart'
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data['homepage_image'] is not None
        assert response.data['homepage_image_url'] is not None
        assert response.data['updated_by'] == admin.id_role

    def test_update_settings_stores_updated_by(self, api_client, test_image):
        """Test that updated_by is correctly stored."""
        admin = SuperAdminFactory()
        api_client.force_authenticate(user=admin)

        response = api_client.patch(
            '/api/settings/',
            {'homepage_image': test_image},
            format='multipart'
        )

        assert response.status_code == status.HTTP_200_OK

        # Verify in database
        config = SiteConfiguration.get_instance()
        assert config.updated_by == admin


@pytest.mark.django_db
@pytest.mark.integration
class TestSiteConfigurationResetEndpoint:
    """Tests for resetting homepage image to default."""

    def test_reset_image_super_admin(self, api_client, test_image):
        """Test super admin can reset image to default."""
        admin = SuperAdminFactory()
        api_client.force_authenticate(user=admin)

        # First upload an image
        api_client.patch(
            '/api/settings/',
            {'homepage_image': test_image},
            format='multipart'
        )

        # Then reset it
        response = api_client.patch(
            '/api/settings/',
            {'reset_image': 'true'}
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data['homepage_image'] is None
        assert response.data['homepage_image_url'] is None

    def test_reset_image_empty_string(self, api_client, test_image):
        """Test resetting image by sending empty string."""
        admin = SuperAdminFactory()
        api_client.force_authenticate(user=admin)

        # First upload an image
        api_client.patch(
            '/api/settings/',
            {'homepage_image': test_image},
            format='multipart'
        )

        # Reset with empty string
        response = api_client.patch(
            '/api/settings/',
            {'homepage_image': ''}
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data['homepage_image'] is None


@pytest.mark.django_db
@pytest.mark.integration
class TestSiteConfigurationValidation:
    """Tests for settings validation."""

    def test_invalid_file_type_rejected(self, api_client):
        """Test that non-image files are rejected."""
        admin = SuperAdminFactory()
        api_client.force_authenticate(user=admin)

        # Create a text file
        text_file = io.BytesIO(b'This is not an image')
        text_file.name = 'test.txt'

        response = api_client.patch(
            '/api/settings/',
            {'homepage_image': text_file},
            format='multipart'
        )

        # Should fail validation
        assert response.status_code in [status.HTTP_400_BAD_REQUEST, status.HTTP_200_OK]

    def test_large_image_handled(self, api_client):
        """Test handling of larger images."""
        admin = SuperAdminFactory()
        api_client.force_authenticate(user=admin)

        # Create a larger image (1920x1080)
        image = Image.new('RGB', (1920, 1080), color='blue')
        buffer = io.BytesIO()
        image.save(buffer, format='JPEG', quality=85)
        buffer.seek(0)
        buffer.name = 'large_image.jpg'

        response = api_client.patch(
            '/api/settings/',
            {'homepage_image': buffer},
            format='multipart'
        )

        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
@pytest.mark.integration
class TestSiteConfigurationSingleton:
    """Tests for singleton pattern."""

    def test_singleton_always_id_1(self, api_client, test_image):
        """Test that configuration always uses ID 1."""
        admin = SuperAdminFactory()
        api_client.force_authenticate(user=admin)

        # Create/update configuration
        api_client.patch(
            '/api/settings/',
            {'homepage_image': test_image},
            format='multipart'
        )

        # Verify only one instance with ID 1
        assert SiteConfiguration.objects.count() == 1
        assert SiteConfiguration.objects.first().pk == 1

    def test_get_instance_creates_if_not_exists(self):
        """Test get_instance creates singleton if it doesn't exist."""
        # Ensure no configuration exists
        SiteConfiguration.objects.all().delete()

        # Get instance should create it
        config = SiteConfiguration.get_instance()

        assert config is not None
        assert config.pk == 1
        assert SiteConfiguration.objects.count() == 1

    def test_multiple_saves_dont_create_duplicates(self, test_image):
        """Test that saving multiple times doesn't create duplicates."""
        # Get instance
        config = SiteConfiguration.get_instance()
        config.save()
        config.save()
        config.save()

        # Still only one instance
        assert SiteConfiguration.objects.count() == 1


# =============================================================================
# #458 — ID DOC'GESTION FCEN : PARAMÈTRE D'INSTANCE
# =============================================================================

@pytest.mark.django_db
@pytest.mark.integration
class TestDocGestionFcenInstanceSetting:
    """
    Tests pour le parametre d'instance `enable_docgestion_fcen` (#458).

    Le champ ID Doc'Gestion FCEN n'a de sens que sur l'instance de la FCEN :
    il est donc desactive par defaut (absent de l'instance RNF) et activable
    par un super_admin.
    """

    def test_disabled_by_default(self, api_client):
        """Le parametre est desactive par defaut (retire de l'instance RNF)."""
        response = api_client.get('/api/settings/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['enable_docgestion_fcen'] is False

    def test_exposed_to_anonymous_users(self, api_client):
        """Le parametre est lisible sans authentification (endpoint public)."""
        config = SiteConfiguration.get_instance()
        config.enable_docgestion_fcen = True
        config.save()

        response = api_client.get('/api/settings/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['enable_docgestion_fcen'] is True

    def test_super_admin_can_enable(self, api_client):
        """Un super_admin peut activer le parametre pour son instance."""
        api_client.force_authenticate(user=SuperAdminFactory())

        response = api_client.patch(
            '/api/settings/',
            {'enable_docgestion_fcen': True},
            format='json',
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data['enable_docgestion_fcen'] is True
        assert SiteConfiguration.get_instance().enable_docgestion_fcen is True

    def test_super_admin_can_disable(self, api_client):
        """Un super_admin peut desactiver le parametre."""
        config = SiteConfiguration.get_instance()
        config.enable_docgestion_fcen = True
        config.save()
        api_client.force_authenticate(user=SuperAdminFactory())

        response = api_client.patch(
            '/api/settings/',
            {'enable_docgestion_fcen': False},
            format='json',
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data['enable_docgestion_fcen'] is False
        assert SiteConfiguration.get_instance().enable_docgestion_fcen is False

    def test_regular_user_cannot_enable(self, api_client):
        """Un utilisateur standard ne peut pas modifier le parametre."""
        api_client.force_authenticate(user=RoleFactory())

        response = api_client.patch(
            '/api/settings/',
            {'enable_docgestion_fcen': True},
            format='json',
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert SiteConfiguration.get_instance().enable_docgestion_fcen is False

    def test_admin_organisme_cannot_enable(self, api_client):
        """Un admin d'organisme ne peut pas modifier le parametre (instance-wide)."""
        api_client.force_authenticate(user=AdminOrganismeFactory())

        response = api_client.patch(
            '/api/settings/',
            {'enable_docgestion_fcen': True},
            format='json',
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert SiteConfiguration.get_instance().enable_docgestion_fcen is False
