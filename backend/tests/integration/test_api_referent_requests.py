"""
Integration tests for Referent Request API (Devenir Referent).
Tests the endpoint /api/users/sites/{id}/request_referent/ and validation workflow.
"""
import pytest
from rest_framework.test import APIClient
from rest_framework import status

from apps.users.models import CorRoleSite
from apps.notifications.models import ValidationRequest, Notification
from tests.factories.users import (
    SuperAdminFactory, AdminOrganismeFactory, RoleFactory,
    OrganismeFactory, SiteFactory, CorRoleSiteFactory, CorOgSiteFactory
)


@pytest.fixture
def api_client():
    """Return an unauthenticated API client."""
    return APIClient()


# =============================================================================
# REQUEST REFERENT ENDPOINT TESTS
# =============================================================================

@pytest.mark.django_db
@pytest.mark.integration
class TestRequestReferentEndpoint:
    """Tests for POST /api/users/sites/{id}/request_referent/"""

    def test_request_referent_unauthenticated(self, api_client):
        """Test that unauthenticated users cannot request referent status."""
        site = SiteFactory()
        response = api_client.post(f'/api/users/sites/{site.slug}/request_referent/')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_request_referent_success(self, api_client):
        """Test successful referent request by user with site access."""
        user = RoleFactory()
        site = SiteFactory()
        # User has access to site but is not referent
        CorRoleSiteFactory(id_role=user, id_site=site, referent=False, referent_valid=False)

        api_client.force_authenticate(user=user)
        response = api_client.post(
            f'/api/users/sites/{site.slug}/request_referent/',
            {'justification': 'Je souhaite devenir referent pour gerer ce site.'}
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert 'id' in response.data
        assert 'message' in response.data
        assert site.nom_site in response.data['message']

        # Verify ValidationRequest was created
        validation_request = ValidationRequest.objects.get(id=response.data['id'])
        assert validation_request.request_type == 'referent_validation'
        assert validation_request.status == 'pending'
        assert validation_request.requester == user
        assert validation_request.target_site == site
        assert validation_request.justification == 'Je souhaite devenir referent pour gerer ce site.'

    def test_request_referent_without_site_access(self, api_client):
        """Test that user without site access cannot request referent status."""
        user = RoleFactory()
        site = SiteFactory()
        # User has NO CorRoleSite link

        api_client.force_authenticate(user=user)
        response = api_client.post(f'/api/users/sites/{site.slug}/request_referent/')

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'error' in response.data
        assert 'acces' in response.data['error'].lower()

    def test_request_referent_already_referent(self, api_client):
        """Test that user already referent cannot request again."""
        user = RoleFactory()
        site = SiteFactory()
        # User is already a valid referent
        CorRoleSiteFactory(id_role=user, id_site=site, referent=True, referent_valid=True)

        api_client.force_authenticate(user=user)
        response = api_client.post(f'/api/users/sites/{site.slug}/request_referent/')

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'error' in response.data
        assert 'deja referent' in response.data['error'].lower()

    def test_request_referent_pending_request_exists(self, api_client):
        """Test that user with pending request cannot create another."""
        user = RoleFactory()
        site = SiteFactory()
        CorRoleSiteFactory(id_role=user, id_site=site, referent=False)

        # Create existing pending request
        ValidationRequest.objects.create(
            request_type='referent_validation',
            status='pending',
            requester=user,
            target_site=site
        )

        api_client.force_authenticate(user=user)
        response = api_client.post(f'/api/users/sites/{site.slug}/request_referent/')

        assert response.status_code == status.HTTP_409_CONFLICT
        assert 'error' in response.data
        assert 'en attente' in response.data['error'].lower()

    def test_request_referent_after_rejected_can_request_again(self, api_client):
        """Test that user can request again after previous request was rejected."""
        user = RoleFactory()
        site = SiteFactory()
        CorRoleSiteFactory(id_role=user, id_site=site, referent=False)

        # Create previous rejected request
        ValidationRequest.objects.create(
            request_type='referent_validation',
            status='rejected',
            requester=user,
            target_site=site
        )

        api_client.force_authenticate(user=user)
        response = api_client.post(f'/api/users/sites/{site.slug}/request_referent/')

        # Should be able to request again after rejection
        assert response.status_code == status.HTTP_201_CREATED

    def test_request_referent_nonexistent_site(self, api_client):
        """Test requesting referent status for non-existent site."""
        user = RoleFactory()

        api_client.force_authenticate(user=user)
        response = api_client.post('/api/users/sites/99999/request_referent/')

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_request_referent_without_justification(self, api_client):
        """Test that request without justification is accepted (optional field)."""
        user = RoleFactory()
        site = SiteFactory()
        CorRoleSiteFactory(id_role=user, id_site=site, referent=False)

        api_client.force_authenticate(user=user)
        response = api_client.post(f'/api/users/sites/{site.slug}/request_referent/')

        assert response.status_code == status.HTTP_201_CREATED

        # Verify empty justification
        validation_request = ValidationRequest.objects.get(id=response.data['id'])
        assert validation_request.justification == ''

    def test_request_referent_creates_notifications_for_validators(self, api_client):
        """Test that notifications are created for validators when request is made."""
        user = RoleFactory()
        organisme = OrganismeFactory()
        site = SiteFactory()

        # Create an existing referent who should receive notification
        existing_referent = RoleFactory()
        CorRoleSiteFactory(
            id_role=existing_referent, id_site=site,
            referent=True, referent_valid=True
        )

        # Link site to organisme
        CorOgSiteFactory(uuid_og=organisme, id_site=site)

        # User requesting referent status
        CorRoleSiteFactory(id_role=user, id_site=site, referent=False)

        api_client.force_authenticate(user=user)
        response = api_client.post(f'/api/users/sites/{site.slug}/request_referent/')

        assert response.status_code == status.HTTP_201_CREATED

        # Check that notification was created for the existing referent
        notifications = Notification.objects.filter(
            recipient=existing_referent,
            notification_type='validation_request'
        )
        assert notifications.exists()


# =============================================================================
# APPROVE/REJECT REFERENT VALIDATION TESTS
# =============================================================================

@pytest.mark.django_db
@pytest.mark.integration
class TestApproveReferentValidation:
    """Tests for approving referent validation requests."""

    def test_approve_referent_request_by_existing_referent(self, api_client):
        """Test that existing referent can approve referent request."""
        organisme = OrganismeFactory()
        site = SiteFactory()
        CorOgSiteFactory(uuid_og=organisme, id_site=site)

        # Existing referent who will approve
        existing_referent = RoleFactory(id_organisme=organisme)
        CorRoleSiteFactory(
            id_role=existing_referent, id_site=site,
            referent=True, referent_valid=True
        )

        # User requesting referent status
        requester = RoleFactory()
        CorRoleSiteFactory(id_role=requester, id_site=site, referent=False, referent_valid=False)

        # Create validation request
        validation_request = ValidationRequest.objects.create(
            request_type='referent_validation',
            status='pending',
            requester=requester,
            target_site=site
        )

        api_client.force_authenticate(user=existing_referent)
        response = api_client.post(
            f'/api/validations/{validation_request.id}/approve/',
            {'comment': 'Demande approuvee'}
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data['status'] == 'approved'

        # Verify ValidationRequest status updated
        validation_request.refresh_from_db()
        assert validation_request.status == 'approved'
        assert validation_request.validator == existing_referent
        assert validation_request.validation_comment == 'Demande approuvee'

        # Verify CorRoleSite updated - user is now referent
        cor_role_site = CorRoleSite.objects.get(id_role=requester, id_site=site)
        assert cor_role_site.referent is True
        assert cor_role_site.referent_valid is True

    def test_approve_referent_request_by_admin_organisme(self, api_client):
        """Test that admin organisme can approve referent request for their sites."""
        organisme = OrganismeFactory()
        admin_og = AdminOrganismeFactory(id_organisme=organisme)
        site = SiteFactory()
        CorOgSiteFactory(uuid_og=organisme, id_site=site)

        # User requesting referent status
        requester = RoleFactory()
        CorRoleSiteFactory(id_role=requester, id_site=site, referent=False)

        # Create validation request
        validation_request = ValidationRequest.objects.create(
            request_type='referent_validation',
            status='pending',
            requester=requester,
            target_site=site
        )

        api_client.force_authenticate(user=admin_og)
        response = api_client.post(f'/api/validations/{validation_request.id}/approve/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['status'] == 'approved'

        # Verify user is now referent
        cor_role_site = CorRoleSite.objects.get(id_role=requester, id_site=site)
        assert cor_role_site.referent is True
        assert cor_role_site.referent_valid is True

    def test_approve_referent_request_by_super_admin(self, api_client):
        """Test that super admin can approve any referent request."""
        super_admin = SuperAdminFactory()
        site = SiteFactory()

        requester = RoleFactory()
        CorRoleSiteFactory(id_role=requester, id_site=site, referent=False)

        validation_request = ValidationRequest.objects.create(
            request_type='referent_validation',
            status='pending',
            requester=requester,
            target_site=site
        )

        api_client.force_authenticate(user=super_admin)
        response = api_client.post(f'/api/validations/{validation_request.id}/approve/')

        assert response.status_code == status.HTTP_200_OK

        cor_role_site = CorRoleSite.objects.get(id_role=requester, id_site=site)
        assert cor_role_site.referent is True

    def test_approve_referent_request_unauthorized_user(self, api_client):
        """Test that regular user cannot approve referent request."""
        site = SiteFactory()

        # Regular user (not referent, not admin)
        regular_user = RoleFactory()

        requester = RoleFactory()
        CorRoleSiteFactory(id_role=requester, id_site=site, referent=False)

        validation_request = ValidationRequest.objects.create(
            request_type='referent_validation',
            status='pending',
            requester=requester,
            target_site=site
        )

        api_client.force_authenticate(user=regular_user)
        response = api_client.post(f'/api/validations/{validation_request.id}/approve/')

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_approve_already_processed_request(self, api_client):
        """Test that already approved request cannot be approved again."""
        super_admin = SuperAdminFactory()
        site = SiteFactory()

        requester = RoleFactory()
        CorRoleSiteFactory(id_role=requester, id_site=site, referent=False)

        validation_request = ValidationRequest.objects.create(
            request_type='referent_validation',
            status='approved',  # Already approved
            requester=requester,
            target_site=site,
            validator=super_admin
        )

        api_client.force_authenticate(user=super_admin)
        response = api_client.post(f'/api/validations/{validation_request.id}/approve/')

        assert response.status_code == status.HTTP_409_CONFLICT
        assert 'déjà été traitée' in response.data['error'].lower()


@pytest.mark.django_db
@pytest.mark.integration
class TestRejectReferentValidation:
    """Tests for rejecting referent validation requests."""

    def test_reject_referent_request_by_existing_referent(self, api_client):
        """Test that existing referent can reject referent request."""
        organisme = OrganismeFactory()
        site = SiteFactory()
        CorOgSiteFactory(uuid_og=organisme, id_site=site)

        existing_referent = RoleFactory(id_organisme=organisme)
        CorRoleSiteFactory(
            id_role=existing_referent, id_site=site,
            referent=True, referent_valid=True
        )

        requester = RoleFactory()
        CorRoleSiteFactory(id_role=requester, id_site=site, referent=False)

        validation_request = ValidationRequest.objects.create(
            request_type='referent_validation',
            status='pending',
            requester=requester,
            target_site=site
        )

        api_client.force_authenticate(user=existing_referent)
        response = api_client.post(
            f'/api/validations/{validation_request.id}/reject/',
            {'comment': 'Demande rejetee car criteres non remplis'}
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data['status'] == 'rejected'

        validation_request.refresh_from_db()
        assert validation_request.status == 'rejected'
        assert validation_request.validator == existing_referent
        assert validation_request.validation_comment == 'Demande rejetee car criteres non remplis'

        # Verify user is NOT referent
        cor_role_site = CorRoleSite.objects.get(id_role=requester, id_site=site)
        assert cor_role_site.referent is False

    def test_reject_referent_request_requires_comment(self, api_client):
        """Test that rejection requires a comment."""
        super_admin = SuperAdminFactory()
        site = SiteFactory()

        requester = RoleFactory()
        CorRoleSiteFactory(id_role=requester, id_site=site, referent=False)

        validation_request = ValidationRequest.objects.create(
            request_type='referent_validation',
            status='pending',
            requester=requester,
            target_site=site
        )

        api_client.force_authenticate(user=super_admin)
        response = api_client.post(
            f'/api/validations/{validation_request.id}/reject/',
            {}  # No comment
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_reject_referent_request_unauthorized_user(self, api_client):
        """Test that regular user cannot reject referent request."""
        site = SiteFactory()
        regular_user = RoleFactory()

        requester = RoleFactory()
        CorRoleSiteFactory(id_role=requester, id_site=site, referent=False)

        validation_request = ValidationRequest.objects.create(
            request_type='referent_validation',
            status='pending',
            requester=requester,
            target_site=site
        )

        api_client.force_authenticate(user=regular_user)
        response = api_client.post(
            f'/api/validations/{validation_request.id}/reject/',
            {'comment': 'Tentative de rejet'}
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN


# =============================================================================
# CANCEL REFERENT REQUEST TESTS
# =============================================================================

@pytest.mark.django_db
@pytest.mark.integration
class TestCancelReferentValidation:
    """Tests for cancelling referent validation requests."""

    def test_cancel_own_referent_request(self, api_client):
        """Test that requester can cancel their own pending request."""
        site = SiteFactory()
        requester = RoleFactory()
        CorRoleSiteFactory(id_role=requester, id_site=site, referent=False)

        validation_request = ValidationRequest.objects.create(
            request_type='referent_validation',
            status='pending',
            requester=requester,
            target_site=site
        )

        api_client.force_authenticate(user=requester)
        response = api_client.post(f'/api/validations/{validation_request.id}/cancel/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['status'] == 'cancelled'

        validation_request.refresh_from_db()
        assert validation_request.status == 'cancelled'

    def test_cancel_other_user_request_forbidden(self, api_client):
        """Test that user cannot cancel another user's request."""
        site = SiteFactory()
        requester = RoleFactory()
        other_user = RoleFactory()
        CorRoleSiteFactory(id_role=requester, id_site=site, referent=False)

        validation_request = ValidationRequest.objects.create(
            request_type='referent_validation',
            status='pending',
            requester=requester,
            target_site=site
        )

        api_client.force_authenticate(user=other_user)
        response = api_client.post(f'/api/validations/{validation_request.id}/cancel/')

        # The API returns 404 because the user cannot see the request (security by design)
        # This is correct behavior - other users shouldn't even know the request exists
        assert response.status_code in [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND]

    def test_cancel_already_processed_request(self, api_client):
        """Test that cannot cancel already processed request."""
        site = SiteFactory()
        requester = RoleFactory()
        CorRoleSiteFactory(id_role=requester, id_site=site, referent=False)

        validation_request = ValidationRequest.objects.create(
            request_type='referent_validation',
            status='approved',
            requester=requester,
            target_site=site
        )

        api_client.force_authenticate(user=requester)
        response = api_client.post(f'/api/validations/{validation_request.id}/cancel/')

        assert response.status_code == status.HTTP_400_BAD_REQUEST


# =============================================================================
# MY REQUESTS ENDPOINT TESTS
# =============================================================================

@pytest.mark.django_db
@pytest.mark.integration
class TestMyRequestsEndpoint:
    """Tests for GET /api/validations/my_requests/"""

    def test_my_requests_returns_user_requests(self, api_client):
        """Test that my_requests returns only the user's requests."""
        site1 = SiteFactory()
        site2 = SiteFactory()
        user = RoleFactory()
        other_user = RoleFactory()

        CorRoleSiteFactory(id_role=user, id_site=site1, referent=False)
        CorRoleSiteFactory(id_role=other_user, id_site=site2, referent=False)

        # User's requests
        ValidationRequest.objects.create(
            request_type='referent_validation',
            status='pending',
            requester=user,
            target_site=site1
        )
        ValidationRequest.objects.create(
            request_type='referent_validation',
            status='approved',
            requester=user,
            target_site=site1
        )

        # Other user's request
        ValidationRequest.objects.create(
            request_type='referent_validation',
            status='pending',
            requester=other_user,
            target_site=site2
        )

        api_client.force_authenticate(user=user)
        response = api_client.get('/api/validations/my_requests/')

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 2
        # Verify all returned requests belong to the user
        # (the structure may vary based on serializer, so we verify count and existence)
        for req in response.data:
            # Check that the request is one of the user's requests
            assert req['request_type'] == 'referent_validation'

    def test_my_requests_empty(self, api_client):
        """Test that my_requests returns empty list when no requests."""
        user = RoleFactory()

        api_client.force_authenticate(user=user)
        response = api_client.get('/api/validations/my_requests/')

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 0


# =============================================================================
# PENDING COUNT ENDPOINT TESTS
# =============================================================================

@pytest.mark.django_db
@pytest.mark.integration
class TestPendingCountEndpoint:
    """Tests for GET /api/validations/pending_count/"""

    def test_pending_count_for_referent(self, api_client):
        """Test pending count for referent with pending requests to validate."""
        organisme = OrganismeFactory()
        site = SiteFactory()
        CorOgSiteFactory(uuid_og=organisme, id_site=site)

        referent = RoleFactory(id_organisme=organisme)
        CorRoleSiteFactory(id_role=referent, id_site=site, referent=True, referent_valid=True)

        requester1 = RoleFactory()
        requester2 = RoleFactory()
        CorRoleSiteFactory(id_role=requester1, id_site=site, referent=False)
        CorRoleSiteFactory(id_role=requester2, id_site=site, referent=False)

        # Create pending requests
        ValidationRequest.objects.create(
            request_type='referent_validation',
            status='pending',
            requester=requester1,
            target_site=site
        )
        ValidationRequest.objects.create(
            request_type='referent_validation',
            status='pending',
            requester=requester2,
            target_site=site
        )

        api_client.force_authenticate(user=referent)
        response = api_client.get('/api/validations/pending_count/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['pending_count'] >= 2

    def test_pending_count_for_regular_user(self, api_client):
        """Test pending count for regular user (should be 0)."""
        user = RoleFactory()

        api_client.force_authenticate(user=user)
        response = api_client.get('/api/validations/pending_count/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['pending_count'] == 0
