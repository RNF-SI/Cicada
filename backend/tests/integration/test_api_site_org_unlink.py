"""
Integration tests for Site-Organisme Unlink validation workflow.
Tests the unassign_site endpoint and the site_org_unlink validation flow.
"""
import pytest
from rest_framework.test import APIClient
from rest_framework import status

from apps.notifications.models import ValidationRequest, Notification
from apps.notifications.services import ValidationService, NotificationService
from apps.users.models import CorOgSite
from tests.factories.users import (
    RoleFactory, SuperAdminFactory, AdminOrganismeFactory,
    OrganismeFactory, SiteFactory, CorOgSiteFactory, CorRoleSiteFactory
)


@pytest.fixture
def api_client():
    """Return an unauthenticated API client."""
    return APIClient()


@pytest.fixture
def super_admin_client(db):
    """Return an authenticated API client with a super admin user."""
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
    return client, admin_og, organisme


@pytest.fixture
def referent_client(db):
    """Return an authenticated API client with a referent user."""
    organisme = OrganismeFactory()
    user = RoleFactory(id_organisme=organisme)
    site = SiteFactory()
    # Link site to organisme
    CorOgSiteFactory(id_site=site, uuid_og=organisme, principal=True)
    # Make user a referent of the site
    CorRoleSiteFactory(id_role=user, id_site=site, referent=True, referent_valid=True)
    client = APIClient()
    client.force_authenticate(user=user)
    return client, user, site, organisme


# =============================================================================
# UNASSIGN SITE ENDPOINT TESTS
# =============================================================================

@pytest.mark.django_db
@pytest.mark.integration
class TestUnassignSiteEndpoint:
    """Tests for DELETE/POST /api/users/organismes/{id}/sites/{site_id}/unassign/ endpoint."""

    def test_unassign_site_requires_authentication(self, api_client, db):
        """Test unassign site endpoint requires authentication."""
        organisme = OrganismeFactory()
        site = SiteFactory()
        CorOgSiteFactory(id_site=site, uuid_og=organisme)

        response = api_client.delete(
            f'/api/users/organismes/{organisme.id_organisme}/sites/{site.id_site}/unassign/'
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_unassign_site_creates_validation_request(self, referent_client, db):
        """Test that unassign site creates a validation request.

        Use a referent (not super_admin/admin_og of the target org) to avoid
        auto-approval and observe the pending validation request.
        """
        client, user, site, organisme = referent_client

        response = client.delete(
            f'/api/users/organismes/{organisme.id_organisme}/sites/{site.id_site}/unassign/'
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['status'] == 'pending'
        assert 'validation_request_id' in response.data

        # Verify validation request was created
        validation_request = ValidationRequest.objects.get(
            pk=response.data['validation_request_id']
        )
        assert validation_request.request_type == 'site_org_unlink'
        assert validation_request.target_site == site
        assert validation_request.requested_organisme == organisme
        assert validation_request.requester == user
        assert validation_request.status == 'pending'

    def test_unassign_site_with_justification(self, super_admin_client, db):
        """Test unassign site with justification."""
        client, admin = super_admin_client
        organisme = OrganismeFactory()
        site = SiteFactory()
        CorOgSiteFactory(id_site=site, uuid_og=organisme)

        response = client.post(
            f'/api/users/organismes/{organisme.id_organisme}/sites/{site.id_site}/unassign/',
            {'justification': 'Organisme ne gère plus ce site'}
        )

        assert response.status_code == status.HTTP_201_CREATED

        validation_request = ValidationRequest.objects.get(
            pk=response.data['validation_request_id']
        )
        assert validation_request.justification == 'Organisme ne gère plus ce site'

    def test_unassign_site_does_not_delete_link_immediately(self, referent_client, db):
        """Test that the site-organisme link is not deleted immediately.

        Use referent to avoid auto-approval (super_admin/admin_og of the
        target org would auto-approve and remove the link instantly).
        """
        client, user, site, organisme = referent_client

        response = client.delete(
            f'/api/users/organismes/{organisme.id_organisme}/sites/{site.id_site}/unassign/'
        )

        assert response.status_code == status.HTTP_201_CREATED

        # Link should still exist (request is pending)
        assert CorOgSite.objects.filter(
            id_site=site, uuid_og=organisme
        ).exists()

    def test_unassign_site_returns_error_if_link_not_exists(self, super_admin_client, db):
        """Test error when trying to unassign a site not linked to organisme."""
        client, admin = super_admin_client
        organisme = OrganismeFactory()
        site = SiteFactory()
        # No CorOgSite link created

        response = client.delete(
            f'/api/users/organismes/{organisme.id_organisme}/sites/{site.id_site}/unassign/'
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert 'error' in response.data

    def test_unassign_site_returns_error_if_pending_request_exists(self, referent_client, db):
        """Test error when a pending request already exists.

        Use referent to avoid auto-approval — only a pending request can be
        a duplicate (auto-approved ones are immediately closed).
        """
        client, user, site, organisme = referent_client

        # Create first request
        response1 = client.delete(
            f'/api/users/organismes/{organisme.id_organisme}/sites/{site.id_site}/unassign/'
        )
        assert response1.status_code == status.HTTP_201_CREATED
        assert response1.data['status'] == 'pending'

        # Try to create second request
        response2 = client.delete(
            f'/api/users/organismes/{organisme.id_organisme}/sites/{site.id_site}/unassign/'
        )
        assert response2.status_code == status.HTTP_400_BAD_REQUEST
        assert 'déjà en cours' in response2.data['error']

    def test_unassign_site_referent_can_request(self, referent_client, db):
        """Test that a site referent can request unlinking an organisme."""
        client, user, site, user_organisme = referent_client

        # Create another organisme linked to the same site
        other_organisme = OrganismeFactory()
        CorOgSiteFactory(id_site=site, uuid_og=other_organisme, principal=False)

        response = client.delete(
            f'/api/users/organismes/{other_organisme.id_organisme}/sites/{site.id_site}/unassign/'
        )

        assert response.status_code == status.HTTP_201_CREATED

    def test_unassign_site_normal_user_cannot_request(self, db):
        """Test that a normal user without site access cannot request unlink."""
        organisme = OrganismeFactory()
        site = SiteFactory()
        CorOgSiteFactory(id_site=site, uuid_og=organisme)

        # Create a user without site access
        user = RoleFactory()
        client = APIClient()
        client.force_authenticate(user=user)

        response = client.delete(
            f'/api/users/organismes/{organisme.id_organisme}/sites/{site.id_site}/unassign/'
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN


# =============================================================================
# VALIDATION SERVICE TESTS
# =============================================================================

@pytest.mark.django_db
@pytest.mark.integration
class TestSiteOrgUnlinkValidationService:
    """Tests for ValidationService.approve_site_org_unlink method."""

    def test_approve_site_org_unlink_deletes_link(self, db):
        """Test that approving site_org_unlink deletes the CorOgSite link."""
        organisme = OrganismeFactory()
        site = SiteFactory()
        CorOgSiteFactory(id_site=site, uuid_og=organisme)
        requester = SuperAdminFactory()
        validator = AdminOrganismeFactory(id_organisme=organisme)

        # Create validation request
        validation_request = ValidationRequest.objects.create(
            request_type='site_org_unlink',
            requester=requester,
            target_site=site,
            requested_organisme=organisme,
            status='pending'
        )

        # Approve the request
        ValidationService.approve_site_org_unlink(
            validation_request, validator, "Approuvé"
        )

        # Link should be deleted
        assert not CorOgSite.objects.filter(
            id_site=site, uuid_og=organisme
        ).exists()

        # Request should be approved
        validation_request.refresh_from_db()
        assert validation_request.status == 'approved'
        assert validation_request.validator == validator

    def test_approve_site_org_unlink_notifies_requester(self, db):
        """Test that approving notifies the requester."""
        organisme = OrganismeFactory()
        site = SiteFactory()
        CorOgSiteFactory(id_site=site, uuid_og=organisme)
        requester = RoleFactory()
        validator = AdminOrganismeFactory(id_organisme=organisme)

        validation_request = ValidationRequest.objects.create(
            request_type='site_org_unlink',
            requester=requester,
            target_site=site,
            requested_organisme=organisme,
            status='pending'
        )

        ValidationService.approve_site_org_unlink(
            validation_request, validator
        )

        # Check notification was created for requester
        notification = Notification.objects.filter(
            recipient=requester,
            notification_type='validation_approved'
        ).first()

        assert notification is not None
        assert 'approuv' in notification.message.lower()  # approuvée ou approuvee

    def test_get_validators_for_site_org_unlink(self, db):
        """Test that validators are the admin_og of the organisme to remove."""
        organisme = OrganismeFactory()
        site = SiteFactory()
        admin_og = AdminOrganismeFactory(id_organisme=organisme)
        requester = SuperAdminFactory()

        validation_request = ValidationRequest.objects.create(
            request_type='site_org_unlink',
            requester=requester,
            target_site=site,
            requested_organisme=organisme,
            status='pending'
        )

        validators = ValidationService.get_validators_for_request(validation_request)

        assert admin_og in validators

    def test_get_validators_falls_back_to_super_admin(self, db):
        """Test that validators fall back to super_admin if no admin_og."""
        organisme = OrganismeFactory()
        site = SiteFactory()
        super_admin = SuperAdminFactory()
        requester = RoleFactory()

        validation_request = ValidationRequest.objects.create(
            request_type='site_org_unlink',
            requester=requester,
            target_site=site,
            requested_organisme=organisme,
            status='pending'
        )

        validators = ValidationService.get_validators_for_request(validation_request)

        assert super_admin in validators


# =============================================================================
# VALIDATION APPROVAL ENDPOINT TESTS
# =============================================================================

@pytest.mark.django_db
@pytest.mark.integration
class TestSiteOrgUnlinkApprovalEndpoint:
    """Tests for POST /api/validations/{id}/approve/ with site_org_unlink."""

    def test_admin_og_can_approve_unlink_request(self, db):
        """Test that admin_og of the organisme can approve the unlink request."""
        organisme = OrganismeFactory()
        admin_og = AdminOrganismeFactory(id_organisme=organisme)
        site = SiteFactory()
        CorOgSiteFactory(id_site=site, uuid_og=organisme)
        requester = SuperAdminFactory()

        # Create validation request
        validation_request = ValidationRequest.objects.create(
            request_type='site_org_unlink',
            requester=requester,
            target_site=site,
            requested_organisme=organisme,
            status='pending'
        )

        client = APIClient()
        client.force_authenticate(user=admin_og)

        response = client.post(
            f'/api/validations/{validation_request.id}/approve/',
            {'comment': 'OK pour retirer notre organisme'}
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data['status'] == 'approved'

        # Link should be deleted
        assert not CorOgSite.objects.filter(
            id_site=site, uuid_og=organisme
        ).exists()

    def test_super_admin_can_approve_unlink_request(self, db):
        """Test that super_admin can approve the unlink request."""
        organisme = OrganismeFactory()
        site = SiteFactory()
        CorOgSiteFactory(id_site=site, uuid_og=organisme)
        requester = RoleFactory()
        super_admin = SuperAdminFactory()

        validation_request = ValidationRequest.objects.create(
            request_type='site_org_unlink',
            requester=requester,
            target_site=site,
            requested_organisme=organisme,
            status='pending'
        )

        client = APIClient()
        client.force_authenticate(user=super_admin)

        response = client.post(
            f'/api/validations/{validation_request.id}/approve/'
        )

        assert response.status_code == status.HTTP_200_OK

    def test_other_admin_og_cannot_approve_unlink_request(self, db):
        """Test that admin_og of another organisme cannot approve."""
        organisme = OrganismeFactory()
        other_organisme = OrganismeFactory()
        other_admin = AdminOrganismeFactory(id_organisme=other_organisme)
        site = SiteFactory()
        CorOgSiteFactory(id_site=site, uuid_og=organisme)
        requester = SuperAdminFactory()

        validation_request = ValidationRequest.objects.create(
            request_type='site_org_unlink',
            requester=requester,
            target_site=site,
            requested_organisme=organisme,
            status='pending'
        )

        client = APIClient()
        client.force_authenticate(user=other_admin)

        response = client.post(
            f'/api/validations/{validation_request.id}/approve/'
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN


# =============================================================================
# VALIDATION REJECTION ENDPOINT TESTS
# =============================================================================

@pytest.mark.django_db
@pytest.mark.integration
class TestSiteOrgUnlinkRejectionEndpoint:
    """Tests for POST /api/validations/{id}/reject/ with site_org_unlink."""

    def test_admin_og_can_reject_unlink_request(self, db):
        """Test that admin_og can reject the unlink request."""
        organisme = OrganismeFactory()
        admin_og = AdminOrganismeFactory(id_organisme=organisme)
        site = SiteFactory()
        CorOgSiteFactory(id_site=site, uuid_og=organisme)
        requester = SuperAdminFactory()

        validation_request = ValidationRequest.objects.create(
            request_type='site_org_unlink',
            requester=requester,
            target_site=site,
            requested_organisme=organisme,
            status='pending'
        )

        client = APIClient()
        client.force_authenticate(user=admin_og)

        response = client.post(
            f'/api/validations/{validation_request.id}/reject/',
            {'comment': 'Nous souhaitons garder la gestion de ce site'}
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data['status'] == 'rejected'

        # Link should still exist
        assert CorOgSite.objects.filter(
            id_site=site, uuid_og=organisme
        ).exists()

        # Request should be rejected
        validation_request.refresh_from_db()
        assert validation_request.status == 'rejected'
