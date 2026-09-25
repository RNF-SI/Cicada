"""
Integration tests for Validations API.
Tests the /api/validations/ endpoints.
"""
import pytest
from rest_framework.test import APIClient
from rest_framework import status

from apps.notifications.models import ValidationRequest
from tests.factories.users import (
    RoleFactory, SuperAdminFactory, AdminOrganismeFactory, OrganismeFactory,
    SiteFactory, CorRoleSiteFactory, CorOgSiteFactory
)
from tests.factories.plans import PlanGestionFactory


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


# =============================================================================
# LIST & FILTER TESTS
# =============================================================================

@pytest.mark.django_db
@pytest.mark.integration
class TestValidationListEndpoint:
    """Tests for GET /api/validations/ endpoint."""

    def test_list_requires_authentication(self, api_client):
        """Test list endpoint requires authentication."""
        response = api_client.get('/api/validations/')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_list_super_admin_sees_all(self, admin_client):
        """Test super admin can list all validation requests."""
        client, admin = admin_client
        site = SiteFactory()
        requester = RoleFactory()

        ValidationRequest.objects.create(
            request_type='site_access', status='pending',
            requester=requester, target_site=site
        )
        ValidationRequest.objects.create(
            request_type='referent_validation', status='approved',
            requester=requester, target_site=site, validator=admin
        )

        response = client.get('/api/validations/')
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) >= 2

    def test_list_filter_by_status(self, admin_client):
        """Test filtering validations by status."""
        client, admin = admin_client
        site = SiteFactory()
        requester = RoleFactory()

        ValidationRequest.objects.create(
            request_type='site_access', status='pending',
            requester=requester, target_site=site
        )
        ValidationRequest.objects.create(
            request_type='site_access', status='approved',
            requester=requester, target_site=site, validator=admin
        )

        response = client.get('/api/validations/', {'status': 'pending'})
        assert response.status_code == status.HTTP_200_OK
        for item in response.data['results']:
            assert item['status'] == 'pending'

    def test_list_filter_by_request_type(self, admin_client):
        """Test filtering validations by request_type."""
        client, admin = admin_client
        site = SiteFactory()
        requester = RoleFactory()

        ValidationRequest.objects.create(
            request_type='site_access', status='pending',
            requester=requester, target_site=site
        )
        ValidationRequest.objects.create(
            request_type='plan_access', status='pending',
            requester=requester
        )

        response = client.get('/api/validations/', {'request_type': 'site_access'})
        assert response.status_code == status.HTTP_200_OK
        for item in response.data['results']:
            assert item['request_type'] == 'site_access'


# =============================================================================
# PENDING COUNT TESTS
# =============================================================================

@pytest.mark.django_db
@pytest.mark.integration
class TestValidationPendingCountEndpoint:
    """Tests for GET /api/validations/pending_count/ endpoint."""

    def test_pending_count_requires_authentication(self, api_client):
        """Test pending_count requires authentication."""
        response = api_client.get('/api/validations/pending_count/')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_pending_count_returns_count(self, admin_client):
        """Test pending_count returns correct count."""
        client, admin = admin_client
        site = SiteFactory()
        requester = RoleFactory()

        ValidationRequest.objects.create(
            request_type='site_access', status='pending',
            requester=requester, target_site=site
        )

        response = client.get('/api/validations/pending_count/')
        assert response.status_code == status.HTTP_200_OK
        assert 'pending_count' in response.data
        assert response.data['pending_count'] >= 1

    def test_pending_count_excludes_non_pending(self, admin_client):
        """Test pending_count only counts pending requests."""
        client, admin = admin_client
        site = SiteFactory()
        requester = RoleFactory()

        ValidationRequest.objects.create(
            request_type='site_access', status='pending',
            requester=requester, target_site=site
        )
        ValidationRequest.objects.create(
            request_type='site_access', status='approved',
            requester=requester, target_site=site, validator=admin
        )

        response = client.get('/api/validations/pending_count/')
        assert response.status_code == status.HTTP_200_OK
        # Count should reflect only pending (not approved)
        assert isinstance(response.data['pending_count'], int)


# =============================================================================
# MY REQUESTS TESTS
# =============================================================================

@pytest.mark.django_db
@pytest.mark.integration
class TestValidationMyRequestsEndpoint:
    """Tests for GET /api/validations/my_requests/ endpoint."""

    def test_my_requests_returns_own_requests(self, authenticated_client):
        """Test my_requests returns only the user's own requests."""
        client, user = authenticated_client
        site = SiteFactory()

        ValidationRequest.objects.create(
            request_type='site_access', status='pending',
            requester=user, target_site=site
        )

        # Another user's request (should not appear)
        other_user = RoleFactory()
        ValidationRequest.objects.create(
            request_type='site_access', status='pending',
            requester=other_user, target_site=site
        )

        response = client.get('/api/validations/my_requests/')
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) >= 1
        for item in response.data:
            assert item['request_type'] == 'site_access'

    def test_my_requests_empty_for_new_user(self):
        """Test my_requests returns empty for user with no requests."""
        user = RoleFactory()
        client = APIClient()
        client.force_authenticate(user=user)

        response = client.get('/api/validations/my_requests/')
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 0


# =============================================================================
# APPROVE / REJECT / CANCEL WORKFLOW TESTS
# =============================================================================

@pytest.mark.django_db
@pytest.mark.integration
class TestValidationWorkflow:
    """Tests for the full approve/reject/cancel workflow."""

    def test_approve_sets_validator_and_status(self, admin_client):
        """Test approving a request sets validator and status."""
        client, admin = admin_client
        site = SiteFactory()
        requester = RoleFactory()
        CorRoleSiteFactory(id_role=requester, id_site=site, referent=False)

        request_obj = ValidationRequest.objects.create(
            request_type='referent_validation', status='pending',
            requester=requester, target_site=site
        )

        response = client.post(f'/api/validations/{request_obj.id}/approve/')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['status'] == 'approved'

        request_obj.refresh_from_db()
        assert request_obj.status == 'approved'
        assert request_obj.validator == admin

    def test_reject_requires_comment(self, admin_client):
        """Test rejecting without comment returns 400."""
        client, admin = admin_client
        site = SiteFactory()
        requester = RoleFactory()

        request_obj = ValidationRequest.objects.create(
            request_type='referent_validation', status='pending',
            requester=requester, target_site=site
        )

        response = client.post(f'/api/validations/{request_obj.id}/reject/', {})
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_reject_with_comment_succeeds(self, admin_client):
        """Test rejecting with comment succeeds."""
        client, admin = admin_client
        site = SiteFactory()
        requester = RoleFactory()
        CorRoleSiteFactory(id_role=requester, id_site=site, referent=False)

        request_obj = ValidationRequest.objects.create(
            request_type='referent_validation', status='pending',
            requester=requester, target_site=site
        )

        response = client.post(
            f'/api/validations/{request_obj.id}/reject/',
            {'comment': 'Insufficient qualifications'}
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data['status'] == 'rejected'

    def test_cancel_own_request(self, authenticated_client):
        """Test user can cancel their own pending request."""
        client, user = authenticated_client
        site = SiteFactory()

        request_obj = ValidationRequest.objects.create(
            request_type='site_access', status='pending',
            requester=user, target_site=site
        )

        response = client.post(f'/api/validations/{request_obj.id}/cancel/')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['status'] == 'cancelled'

    def test_cancel_site_creation_deletes_orphaned_site(self, authenticated_client):
        """#467 — Annuler une création de site supprime le site orphelin (inactif)
        et sa demande de validation."""
        from apps.users.models import Site

        client, user = authenticated_client
        site = SiteFactory(nom_site='Site en attente', active=False)

        request_obj = ValidationRequest.objects.create(
            request_type='site_creation', status='pending',
            requester=user, target_site=site
        )

        response = client.post(f'/api/validations/{request_obj.id}/cancel/')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['status'] == 'cancelled'

        # Le site orphelin et la demande sont supprimés
        assert not Site.objects.filter(pk=site.pk).exists()
        assert not ValidationRequest.objects.filter(pk=request_obj.id).exists()

    def test_cancel_site_creation_keeps_active_site(self, authenticated_client):
        """#467 — Si le site a déjà été validé (actif), l'annulation ne le
        supprime pas (garde-fou)."""
        from apps.users.models import Site

        client, user = authenticated_client
        site = SiteFactory(nom_site='Site validé', active=True)

        request_obj = ValidationRequest.objects.create(
            request_type='site_creation', status='pending',
            requester=user, target_site=site
        )

        response = client.post(f'/api/validations/{request_obj.id}/cancel/')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['status'] == 'cancelled'

        # Le site actif est conservé
        assert Site.objects.filter(pk=site.pk).exists()

    def test_cancel_other_users_request_fails(self, authenticated_client):
        """Test user cannot cancel another user's request."""
        client, user = authenticated_client
        other_user = RoleFactory()
        site = SiteFactory()

        request_obj = ValidationRequest.objects.create(
            request_type='site_access', status='pending',
            requester=other_user, target_site=site
        )

        response = client.post(f'/api/validations/{request_obj.id}/cancel/')
        assert response.status_code in [
            status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND
        ]

    def test_approve_already_processed_returns_conflict(self, admin_client):
        """Test approving an already-processed request returns 409."""
        client, admin = admin_client
        site = SiteFactory()
        requester = RoleFactory()

        request_obj = ValidationRequest.objects.create(
            request_type='referent_validation', status='approved',
            requester=requester, target_site=site, validator=admin
        )

        response = client.post(f'/api/validations/{request_obj.id}/approve/')
        assert response.status_code == status.HTTP_409_CONFLICT

    def test_regular_user_cannot_approve(self, authenticated_client):
        """Test regular user cannot approve requests."""
        client, user = authenticated_client
        site = SiteFactory()
        requester = RoleFactory()

        request_obj = ValidationRequest.objects.create(
            request_type='referent_validation', status='pending',
            requester=requester, target_site=site
        )

        response = client.post(f'/api/validations/{request_obj.id}/approve/')
        assert response.status_code == status.HTTP_403_FORBIDDEN


# =============================================================================
# PLAN ACCESS REQUEST TESTS
# =============================================================================

@pytest.mark.django_db
@pytest.mark.integration
class TestValidationPlanAccessRequest:
    """Tests for POST /api/validations/request_plan_access/ endpoint."""

    def test_request_plan_access_success(self, authenticated_client):
        """Test successful plan access request."""
        client, user = authenticated_client
        site = SiteFactory()
        plan = PlanGestionFactory(statut='valide', sites=[site])

        response = client.post('/api/validations/request_plan_access/', {
            'plan_id': plan.id_pg,
            'justification': 'Need access for work'
        })
        assert response.status_code == status.HTTP_201_CREATED
        assert 'id' in response.data

    def test_request_plan_access_missing_plan_id(self, authenticated_client):
        """Test error when plan_id is missing."""
        client, user = authenticated_client

        response = client.post('/api/validations/request_plan_access/', {})
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_request_plan_access_nonexistent_plan(self, authenticated_client):
        """Test error when plan does not exist."""
        client, user = authenticated_client

        response = client.post('/api/validations/request_plan_access/', {
            'plan_id': 99999
        })
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_request_plan_access_already_referent(self, authenticated_client):
        """Test error when user already has access as referent."""
        client, user = authenticated_client
        site = SiteFactory()
        plan = PlanGestionFactory(statut='valide', sites=[site], referents=[user])

        response = client.post('/api/validations/request_plan_access/', {
            'plan_id': plan.id_pg
        })
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_admin_og_of_the_plan_organisme_cannot_request_access(self):
        """#657 — Un admin_og gère déjà les plans des sites de son organisme."""
        organisme = OrganismeFactory()
        admin_og = AdminOrganismeFactory(id_organisme=organisme)
        site = SiteFactory()
        CorOgSiteFactory(id_site=site, uuid_og=organisme)
        plan = PlanGestionFactory(statut='valide', sites=[site])

        client = APIClient()
        client.force_authenticate(user=admin_og)
        response = client.post('/api/validations/request_plan_access/', {
            'plan_id': plan.id_pg,
        })

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert not ValidationRequest.objects.filter(
            request_type='plan_access', target_plan=plan
        ).exists()

    def test_admin_og_can_still_request_access_to_a_plan_outside_his_organisme(self):
        """#657 ne ferme que le périmètre de l'organisme, pas les autres plans."""
        admin_og = AdminOrganismeFactory(id_organisme=OrganismeFactory())
        site = SiteFactory()
        CorOgSiteFactory(id_site=site, uuid_og=OrganismeFactory())
        plan = PlanGestionFactory(statut='valide', sites=[site])

        client = APIClient()
        client.force_authenticate(user=admin_og)
        response = client.post('/api/validations/request_plan_access/', {
            'plan_id': plan.id_pg,
            'justification': 'Besoin de consulter ce plan',
        })

        assert response.status_code == status.HTTP_201_CREATED

    def test_super_admin_cannot_request_plan_access(self, admin_client):
        """#657 — Le super admin voit tous les plans : rien à demander."""
        client, _admin = admin_client
        plan = PlanGestionFactory(statut='valide', sites=[SiteFactory()])

        response = client.post('/api/validations/request_plan_access/', {
            'plan_id': plan.id_pg,
        })
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_simple_user_linked_to_a_site_can_still_request_access(self):
        """Un utilisateur simple lié à un site du plan garde le droit de demander."""
        organisme = OrganismeFactory()
        user = RoleFactory(id_organisme=organisme)
        site = SiteFactory()
        CorOgSiteFactory(id_site=site, uuid_og=organisme)
        CorRoleSiteFactory(id_role=user, id_site=site)
        plan = PlanGestionFactory(statut='valide', sites=[site])

        client = APIClient()
        client.force_authenticate(user=user)
        response = client.post('/api/validations/request_plan_access/', {
            'plan_id': plan.id_pg,
            'justification': 'Je souhaite devenir référent',
        })

        assert response.status_code == status.HTTP_201_CREATED

    def test_request_plan_access_duplicate_pending(self, authenticated_client):
        """Test error when a pending request already exists."""
        client, user = authenticated_client
        site = SiteFactory()
        plan = PlanGestionFactory(statut='valide', sites=[site])

        # First request
        client.post('/api/validations/request_plan_access/', {
            'plan_id': plan.id_pg,
            'justification': 'First request'
        })

        # Duplicate request
        response = client.post('/api/validations/request_plan_access/', {
            'plan_id': plan.id_pg,
            'justification': 'Second request'
        })
        assert response.status_code == status.HTTP_400_BAD_REQUEST


# =============================================================================
# #653 — CONTEXTE « ADMINISTRATEURS DE L'ORGANISME » À L'ACCEPTATION D'UN COMPTE
# =============================================================================

@pytest.mark.django_db
@pytest.mark.integration
class TestRegistrationOrganismeAdminsContext:
    """Le validateur d'une inscription doit savoir si l'organisme a déjà un admin_og (#653)."""

    def _registration(self, organisme=None):
        return ValidationRequest.objects.create(
            request_type='user_registration',
            status='pending',
            requester=None,
            requested_organisme=organisme,
        )

    def test_detail_lists_existing_admins(self, admin_client):
        client, _admin = admin_client
        organisme = OrganismeFactory()
        admin_og = AdminOrganismeFactory(id_organisme=organisme, nom_role='Dupont', prenom_role='Marie')
        vr = self._registration(organisme)

        response = client.get(f'/api/validations/{vr.id}/')
        assert response.status_code == status.HTTP_200_OK
        ctx = response.data['organisme_admins']
        assert ctx['is_new_organisme'] is False
        assert ctx['count'] == 1
        assert ctx['admins'][0]['id'] == admin_og.id_role
        assert ctx['admins'][0]['nom_complet'] == 'Marie Dupont'

    def test_detail_reports_organisme_without_admin(self, admin_client):
        client, _admin = admin_client
        organisme = OrganismeFactory()
        RoleFactory(id_organisme=organisme)  # simple utilisateur : pas un admin_og
        vr = self._registration(organisme)

        response = client.get(f'/api/validations/{vr.id}/')
        assert response.data['organisme_admins']['count'] == 0
        assert response.data['organisme_admins']['admins'] == []

    def test_inactive_admin_is_not_counted(self, admin_client):
        client, _admin = admin_client
        organisme = OrganismeFactory()
        AdminOrganismeFactory(id_organisme=organisme, active=False)
        vr = self._registration(organisme)

        assert client.get(f'/api/validations/{vr.id}/').data['organisme_admins']['count'] == 0

    def test_new_organisme_is_flagged(self, admin_client):
        client, _admin = admin_client
        vr = self._registration(None)
        ValidationRequest.objects.create(
            request_type='organisme_creation',
            status='pending',
            requester=None,
            requested_data={'nom_organisme': 'CEN Nouvelle-Aquitaine'},
            related_request=vr,
        )

        ctx = client.get(f'/api/validations/{vr.id}/').data['organisme_admins']
        assert ctx['is_new_organisme'] is True
        assert ctx['count'] == 0

    def test_other_request_types_have_no_context(self, admin_client):
        client, _admin = admin_client
        site = SiteFactory()
        vr = ValidationRequest.objects.create(
            request_type='site_access',
            status='pending',
            requester=RoleFactory(),
            target_site=site,
        )

        assert client.get(f'/api/validations/{vr.id}/').data['organisme_admins'] is None

    def test_super_admin_is_not_notified_when_organisme_has_an_admin(self):
        """La notification d'inscription ne remonte au super admin que faute d'admin_og (#653)."""
        from apps.notifications.services import ValidationService

        organisme = OrganismeFactory()
        admin_og = AdminOrganismeFactory(id_organisme=organisme)
        super_admin = SuperAdminFactory()
        vr = self._registration(organisme)

        validators = ValidationService.get_validators_for_request(vr)
        assert admin_og in validators
        assert super_admin not in validators

    def test_super_admin_is_notified_when_organisme_has_no_admin(self):
        from apps.notifications.services import ValidationService

        organisme = OrganismeFactory()
        super_admin = SuperAdminFactory()
        vr = self._registration(organisme)

        assert super_admin in ValidationService.get_validators_for_request(vr)
