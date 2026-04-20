"""
Integration tests for the public registration endpoint and the
registration approval flow, with a focus on the optional `identifiant` field.
"""
import pytest
from rest_framework.test import APIClient
from rest_framework import status

from apps.notifications.models import PendingUser, ValidationRequest
from apps.notifications.services import ValidationService
from apps.users.models import Role
from tests.factories.users import OrganismeFactory, SuperAdminFactory, RoleFactory
from tests.factories.notifications import PendingUserFactory


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def organisme(db):
    return OrganismeFactory(nom_organisme='Test Org')


def _payload(organisme, **overrides):
    base = {
        'email': 'newuser@test.fr',
        'password': 'StrongPass123!',
        'password_confirm': 'StrongPass123!',
        'nom_role': 'Doe',
        'prenom_role': 'Jane',
        'requested_organisme_id': organisme.id_organisme,
        'justification': 'Test registration.',
    }
    base.update(overrides)
    return base


@pytest.mark.django_db
@pytest.mark.integration
class TestPublicRegistrationIdentifiant:
    """Tests for /api/auth/register/ with the optional identifiant field."""

    URL = '/api/auth/register/'

    def test_register_with_identifiant_creates_pending_user(self, api_client, organisme):
        response = api_client.post(
            self.URL,
            _payload(organisme, identifiant='janed'),
            format='json',
        )

        assert response.status_code == status.HTTP_201_CREATED
        pending = PendingUser.objects.get(email='newuser@test.fr')
        assert pending.identifiant == 'janed'

    def test_register_without_identifiant_still_works(self, api_client, organisme):
        """Identifiant is optional — registration without it must succeed (backward compat)."""
        response = api_client.post(self.URL, _payload(organisme), format='json')

        assert response.status_code == status.HTTP_201_CREATED
        pending = PendingUser.objects.get(email='newuser@test.fr')
        assert pending.identifiant is None

    def test_register_blank_identifiant_stored_as_empty(self, api_client, organisme):
        """Empty string identifiant is allowed and stored as null."""
        response = api_client.post(
            self.URL,
            _payload(organisme, identifiant=''),
            format='json',
        )

        assert response.status_code == status.HTTP_201_CREATED
        pending = PendingUser.objects.get(email='newuser@test.fr')
        assert not pending.identifiant  # None or '' both acceptable

    def test_register_duplicate_identifiant_against_role_rejected(
        self, api_client, organisme
    ):
        RoleFactory(identifiant='taken', email='existing@test.fr')

        response = api_client.post(
            self.URL,
            _payload(organisme, identifiant='taken'),
            format='json',
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'identifiant' in response.data
        assert not PendingUser.objects.filter(email='newuser@test.fr').exists()

    def test_register_duplicate_identifiant_against_pending_user_rejected(
        self, api_client, organisme
    ):
        PendingUserFactory(identifiant='alreadypending')

        response = api_client.post(
            self.URL,
            _payload(organisme, identifiant='alreadypending'),
            format='json',
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'identifiant' in response.data

    def test_register_duplicate_identifiant_case_insensitive(
        self, api_client, organisme
    ):
        RoleFactory(identifiant='MixedCase', email='mixed@test.fr')

        response = api_client.post(
            self.URL,
            _payload(organisme, identifiant='mixedcase'),
            format='json',
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
@pytest.mark.integration
class TestApprovalCopiesIdentifiant:
    """Approval of a registration must copy identifiant onto the new Role."""

    def test_approval_copies_identifiant_to_role(self, db):
        organisme = OrganismeFactory()
        validator = SuperAdminFactory()
        pending = PendingUserFactory(
            email='approveme@test.fr',
            identifiant='approveme',
            requested_organisme=organisme,
        )

        user = ValidationService.approve_registration(
            pending.validation_request, validator
        )

        assert user is not None
        assert user.identifiant == 'approveme'
        assert user.email == 'approveme@test.fr'
        assert not PendingUser.objects.filter(pk=pending.pk).exists()

    def test_approval_without_identifiant_leaves_role_identifiant_null(self, db):
        organisme = OrganismeFactory()
        validator = SuperAdminFactory()
        pending = PendingUserFactory(
            email='noident@test.fr',
            identifiant=None,
            requested_organisme=organisme,
        )

        user = ValidationService.approve_registration(
            pending.validation_request, validator
        )

        assert user.identifiant is None
