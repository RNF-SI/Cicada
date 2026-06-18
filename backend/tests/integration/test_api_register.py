"""
Integration tests for the public registration endpoint and the
registration approval flow, with a focus on the optional `identifiant` field.
"""
import pytest
from rest_framework.test import APIClient
from rest_framework import status

from apps.notifications.models import PendingUser, ValidationRequest
from apps.notifications.services import ValidationService
from apps.users.models import BibOrganismes, Role
from tests.factories.users import OrganismeFactory, SuperAdminFactory, RoleFactory
from tests.factories.notifications import PendingUserFactory


NEW_ORG = {
    'nom_organisme': 'Conservatoire Test',
    'adresse_organisme': '1 rue de la Test',
    'cp_organisme': '21000',
    'ville_organisme': 'Dijon',
    'tel_organisme': '0380000000',
    'email_organisme': 'contact@orga-test.fr',
    'url_organisme': 'https://orga-test.fr',
}


def _payload_new_org(**overrides):
    """Payload d'inscription demandant la création d'un nouvel organisme."""
    base = {
        'email': 'newuser@test.fr',
        'password': 'StrongPass123!',
        'password_confirm': 'StrongPass123!',
        'nom_role': 'Doe',
        'prenom_role': 'Jane',
        'new_organisme': dict(NEW_ORG),
        'justification': 'Mon organisme n\'existe pas encore.',
    }
    base.update(overrides)
    return base


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
class TestRegistrationRequiresOrganisme:
    """Organisme is now mandatory at registration (no silent null acceptance)."""

    URL = '/api/auth/register/'

    def test_register_without_organisme_id_rejected(self, api_client, organisme):
        payload = _payload(organisme)
        payload.pop('requested_organisme_id')

        response = api_client.post(self.URL, payload, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'requested_organisme_id' in response.data
        assert not PendingUser.objects.filter(email='newuser@test.fr').exists()

    def test_register_with_null_organisme_id_rejected(self, api_client, organisme):
        response = api_client.post(
            self.URL,
            _payload(organisme, requested_organisme_id=None),
            format='json',
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'requested_organisme_id' in response.data
        assert not PendingUser.objects.filter(email='newuser@test.fr').exists()

    def test_register_with_unknown_organisme_id_rejected(self, api_client, organisme):
        response = api_client.post(
            self.URL,
            _payload(organisme, requested_organisme_id=999999),
            format='json',
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'requested_organisme_id' in response.data
        assert not PendingUser.objects.filter(email='newuser@test.fr').exists()


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


@pytest.mark.django_db
@pytest.mark.integration
class TestApprovalRequiresOrganisme:
    """Approval must refuse when the pending registration lost its organisme."""

    def test_approval_refused_when_organisme_missing(self, db):
        validator = SuperAdminFactory()
        pending = PendingUserFactory(
            email='orphan@test.fr',
            requested_organisme=None,
        )

        with pytest.raises(ValueError, match="organisme_id_override"):
            ValidationService.approve_registration(
                pending.validation_request, validator
            )

        # PendingUser must remain (transaction safety)
        assert PendingUser.objects.filter(pk=pending.pk).exists()
        assert not Role.objects.filter(email='orphan@test.fr').exists()

    def test_approval_succeeds_with_organisme_override(self, db):
        validator = SuperAdminFactory()
        fallback_org = OrganismeFactory(nom_organisme='Fallback Org')
        pending = PendingUserFactory(
            email='rescued@test.fr',
            requested_organisme=None,
        )

        user = ValidationService.approve_registration(
            pending.validation_request,
            validator,
            organisme_override=fallback_org,
        )

        assert user is not None
        assert user.id_organisme == fallback_org

    def test_approval_uses_pending_org_when_present_ignoring_override(self, db):
        """If pending has its own organisme, the override is ignored (priority to original choice)."""
        validator = SuperAdminFactory()
        original_org = OrganismeFactory(nom_organisme='Original')
        override_org = OrganismeFactory(nom_organisme='Override')
        pending = PendingUserFactory(
            email='keep.original@test.fr',
            requested_organisme=original_org,
        )

        user = ValidationService.approve_registration(
            pending.validation_request,
            validator,
            organisme_override=override_org,
        )

        assert user.id_organisme == original_org


@pytest.mark.django_db
@pytest.mark.integration
class TestApprovalEndpointWithOverride:
    """End-to-end: HTTP approval endpoint accepts organisme_id_override."""

    def test_endpoint_rejects_without_organisme(self, api_client):
        validator = SuperAdminFactory()
        validator.set_password('Pass123!')
        validator.save()
        pending = PendingUserFactory(email='endpoint.refuse@test.fr', requested_organisme=None)

        api_client.force_authenticate(user=validator)
        response = api_client.post(
            f'/api/validations/{pending.validation_request.id}/approve/',
            {},
            format='json',
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'organisme' in response.data['error'].lower()

    def test_endpoint_accepts_override(self, api_client):
        validator = SuperAdminFactory()
        validator.set_password('Pass123!')
        validator.save()
        fallback_org = OrganismeFactory(nom_organisme='Fallback HTTP')
        pending = PendingUserFactory(email='endpoint.rescue@test.fr', requested_organisme=None)

        api_client.force_authenticate(user=validator)
        response = api_client.post(
            f'/api/validations/{pending.validation_request.id}/approve/',
            {'organisme_id_override': fallback_org.id_organisme},
            format='json',
        )

        assert response.status_code == status.HTTP_200_OK
        user = Role.objects.get(email='endpoint.rescue@test.fr')
        assert user.id_organisme == fallback_org


@pytest.mark.django_db
@pytest.mark.integration
class TestRegistrationWithNewOrganisme:
    """Inscription avec demande de création d'un nouvel organisme (#385)."""

    URL = '/api/auth/register/'

    def test_register_with_new_organisme_creates_two_linked_requests(self, api_client):
        response = api_client.post(self.URL, _payload_new_org(), format='json')

        assert response.status_code == status.HTTP_201_CREATED

        pending = PendingUser.objects.get(email='newuser@test.fr')
        # Le compte n'a pas encore d'organisme (il sera créé puis rattaché)
        assert pending.requested_organisme is None

        reg = pending.validation_request
        assert reg.request_type == 'user_registration'

        org_req = ValidationRequest.objects.get(request_type='organisme_creation')
        assert org_req.related_request_id == reg.id
        assert org_req.status == 'pending'
        assert org_req.requested_data['nom_organisme'] == NEW_ORG['nom_organisme']
        assert org_req.requested_data['cp_organisme'] == '21000'
        # Aucun organisme réellement créé tant que non validé
        assert not BibOrganismes.objects.filter(nom_organisme=NEW_ORG['nom_organisme']).exists()

    def test_register_rejects_both_organisme_and_new_organisme(self, api_client):
        org = OrganismeFactory()
        payload = _payload_new_org(requested_organisme_id=org.id_organisme)

        response = api_client.post(self.URL, payload, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert not PendingUser.objects.filter(email='newuser@test.fr').exists()

    def test_register_new_organisme_missing_name_rejected(self, api_client):
        payload = _payload_new_org(new_organisme={'ville_organisme': 'Dijon'})

        response = api_client.post(self.URL, payload, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_approve_organisme_creation_creates_org_and_links_pending(self, api_client):
        api_client.post(self.URL, _payload_new_org(), format='json')
        validator = SuperAdminFactory()
        org_req = ValidationRequest.objects.get(request_type='organisme_creation')

        organisme = ValidationService.approve_organisme_creation(org_req, validator)

        assert organisme.nom_organisme == NEW_ORG['nom_organisme']
        assert organisme.ville_organisme == 'Dijon'
        org_req.refresh_from_db()
        assert org_req.status == 'approved'

        # L'organisme est rattaché au compte en attente et à sa demande
        pending = PendingUser.objects.get(email='newuser@test.fr')
        assert pending.requested_organisme_id == organisme.id_organisme
        assert pending.validation_request.requested_organisme_id == organisme.id_organisme

    def test_approve_registration_blocked_until_organisme_approved(self, api_client):
        api_client.post(self.URL, _payload_new_org(), format='json')
        validator = SuperAdminFactory()
        pending = PendingUser.objects.get(email='newuser@test.fr')

        with pytest.raises(ValueError, match="création d'organisme"):
            ValidationService.approve_registration(pending.validation_request, validator)

        assert not Role.objects.filter(email='newuser@test.fr').exists()

    def test_full_flow_org_then_account(self, api_client):
        api_client.post(self.URL, _payload_new_org(), format='json')
        validator = SuperAdminFactory()
        org_req = ValidationRequest.objects.get(request_type='organisme_creation')
        reg = org_req.related_request

        organisme = ValidationService.approve_organisme_creation(org_req, validator)
        user = ValidationService.approve_registration(reg, validator)

        assert user.email == 'newuser@test.fr'
        assert user.id_organisme == organisme
        assert not PendingUser.objects.filter(email='newuser@test.fr').exists()

    def test_endpoint_approve_account_before_organisme_returns_400_and_keeps_pending(self, api_client):
        """Approuver le compte AVANT l'organisme via l'API : 400 explicite, rien de cassé."""
        api_client.post(self.URL, _payload_new_org(), format='json')
        validator = SuperAdminFactory()
        reg = ValidationRequest.objects.get(request_type='user_registration')

        api_client.force_authenticate(user=validator)
        response = api_client.post(
            f'/api/validations/{reg.id}/approve/', {}, format='json'
        )

        # Erreur métier propre (pas un 500)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'organisme' in response.data['error'].lower()

        # La demande reste en attente (transaction annulée) et aucun compte créé
        reg.refresh_from_db()
        assert reg.status == 'pending'
        assert not Role.objects.filter(email='newuser@test.fr').exists()

        # Dans le bon ordre (organisme puis compte) : tout fonctionne
        org_req = ValidationRequest.objects.get(request_type='organisme_creation')
        api_client.post(f'/api/validations/{org_req.id}/approve/', {}, format='json')
        response2 = api_client.post(f'/api/validations/{reg.id}/approve/', {}, format='json')
        assert response2.status_code == status.HTTP_200_OK
        assert Role.objects.filter(email='newuser@test.fr').exists()

    def test_reject_organisme_creation_cascades_to_registration(self, api_client):
        api_client.post(self.URL, _payload_new_org(), format='json')
        validator = SuperAdminFactory()
        org_req = ValidationRequest.objects.get(request_type='organisme_creation')
        reg = org_req.related_request

        ValidationService.reject_request(org_req, validator, comment='Organisme non pertinent.')

        org_req.refresh_from_db()
        reg.refresh_from_db()
        assert org_req.status == 'rejected'
        assert reg.status == 'rejected'
        assert not BibOrganismes.objects.filter(nom_organisme=NEW_ORG['nom_organisme']).exists()
