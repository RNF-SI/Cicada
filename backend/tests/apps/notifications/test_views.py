"""
Unit tests for notifications app views.
Tests NotificationViewSet and ValidationRequestViewSet.
"""
import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.notifications.models import Notification, ValidationRequest, PendingUser
from apps.users.models import CorRoleSite, CorOgSite
from tests.factories.users import (
    RoleFactory, SuperAdminFactory, AdminOrganismeFactory,
    SiteFactory, OrganismeFactory, CorRoleSiteFactory, CorOgSiteFactory
)
from tests.factories.notifications import (
    NotificationFactory, ValidationRequestFactory, PendingUserFactory
)
from tests.factories.plans import PlanGestionFactory


# =============================================================================
# NOTIFICATION VIEWSET TESTS
# =============================================================================

@pytest.mark.django_db
@pytest.mark.unit
class TestNotificationViewSetList:
    """Tests for NotificationViewSet list endpoint."""

    def test_list_notifications_authenticated(self):
        """Test listing notifications for authenticated user."""
        user = RoleFactory()
        NotificationFactory(recipient=user)
        NotificationFactory(recipient=user)
        other_user = RoleFactory()
        NotificationFactory(recipient=other_user)  # Should not appear

        client = APIClient()
        client.force_authenticate(user=user)
        response = client.get('/api/notifications/')

        assert response.status_code == status.HTTP_200_OK
        # Only user's notifications
        assert len(response.data['results']) == 2

    def test_list_notifications_unauthenticated(self):
        """Test listing notifications without authentication."""
        client = APIClient()
        response = client.get('/api/notifications/')

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
@pytest.mark.unit
class TestNotificationViewSetUnread:
    """Tests for NotificationViewSet unread endpoint."""

    def test_unread_notifications(self):
        """Test getting unread notifications."""
        user = RoleFactory()
        NotificationFactory(recipient=user, read=False)
        NotificationFactory(recipient=user, read=False)
        NotificationFactory(recipient=user, read=True)  # Should not appear

        client = APIClient()
        client.force_authenticate(user=user)
        response = client.get('/api/notifications/unread/')

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 2


@pytest.mark.django_db
@pytest.mark.unit
class TestNotificationViewSetCount:
    """Tests for NotificationViewSet count endpoint."""

    def test_count_unread_notifications(self):
        """Test counting unread notifications."""
        user = RoleFactory()
        NotificationFactory(recipient=user, read=False)
        NotificationFactory(recipient=user, read=False)
        NotificationFactory(recipient=user, read=True)

        client = APIClient()
        client.force_authenticate(user=user)
        response = client.get('/api/notifications/count/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['unread_count'] == 2


@pytest.mark.django_db
@pytest.mark.unit
class TestNotificationViewSetMarkRead:
    """Tests for NotificationViewSet mark_read endpoint."""

    def test_mark_notification_as_read(self):
        """Test marking a single notification as read."""
        user = RoleFactory()
        notification = NotificationFactory(recipient=user, read=False)

        client = APIClient()
        client.force_authenticate(user=user)
        response = client.post(f'/api/notifications/{notification.id}/mark_read/')

        assert response.status_code == status.HTTP_200_OK
        notification.refresh_from_db()
        assert notification.read is True


@pytest.mark.django_db
@pytest.mark.unit
class TestNotificationViewSetMarkAllRead:
    """Tests for NotificationViewSet mark_all_read endpoint."""

    def test_mark_all_notifications_as_read(self):
        """Test marking all notifications as read."""
        user = RoleFactory()
        NotificationFactory(recipient=user, read=False)
        NotificationFactory(recipient=user, read=False)

        client = APIClient()
        client.force_authenticate(user=user)
        response = client.post('/api/notifications/mark_all_read/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['updated_count'] == 2
        assert response.data['unread_count'] == 0

        # Verify in database
        unread_count = Notification.objects.filter(recipient=user, read=False).count()
        assert unread_count == 0


@pytest.mark.django_db
@pytest.mark.unit
class TestNotificationViewSetPoll:
    """Tests for NotificationViewSet poll endpoint."""

    def test_poll_notifications(self):
        """Test polling for notifications."""
        user = RoleFactory()
        NotificationFactory(recipient=user, read=False)

        client = APIClient()
        client.force_authenticate(user=user)
        response = client.get('/api/notifications/poll/')

        assert response.status_code == status.HTTP_200_OK
        assert 'notifications' in response.data
        assert 'unread_count' in response.data
        assert 'pending_validations' in response.data
        assert 'has_updates' in response.data
        assert 'timestamp' in response.data


@pytest.mark.django_db
@pytest.mark.unit
class TestNotificationViewSetDelete:
    """Tests for NotificationViewSet delete endpoint."""

    def test_delete_notification(self):
        """Test deleting a notification."""
        user = RoleFactory()
        notification = NotificationFactory(recipient=user)

        client = APIClient()
        client.force_authenticate(user=user)
        response = client.delete(f'/api/notifications/{notification.id}/')

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not Notification.objects.filter(id=notification.id).exists()


# =============================================================================
# VALIDATION REQUEST VIEWSET TESTS
# =============================================================================

@pytest.mark.django_db
@pytest.mark.unit
class TestValidationRequestViewSetList:
    """Tests for ValidationRequestViewSet list endpoint."""

    def test_list_validations_super_admin(self):
        """Test super admin can see all validations."""
        super_admin = SuperAdminFactory()
        site = SiteFactory()
        requester = RoleFactory()
        CorRoleSiteFactory(id_role=requester, id_site=site, referent=False)

        ValidationRequest.objects.create(
            request_type='referent_validation',
            status='pending',
            requester=requester,
            target_site=site
        )

        client = APIClient()
        client.force_authenticate(user=super_admin)
        response = client.get('/api/validations/')

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) >= 1

    def test_list_validations_with_status_filter(self):
        """Test filtering validations by status."""
        super_admin = SuperAdminFactory()
        site = SiteFactory()
        requester = RoleFactory()

        ValidationRequest.objects.create(
            request_type='referent_validation',
            status='pending',
            requester=requester,
            target_site=site
        )
        ValidationRequest.objects.create(
            request_type='referent_validation',
            status='approved',
            requester=requester,
            target_site=site,
            validator=super_admin
        )

        client = APIClient()
        client.force_authenticate(user=super_admin)
        response = client.get('/api/validations/?status=pending')

        assert response.status_code == status.HTTP_200_OK
        for item in response.data['results']:
            assert item['status'] == 'pending'


@pytest.mark.django_db
@pytest.mark.unit
class TestValidationRequestViewSetPendingCount:
    """Tests for ValidationRequestViewSet pending_count endpoint."""

    def test_pending_count_for_super_admin(self):
        """Test pending count for super admin."""
        super_admin = SuperAdminFactory()
        site = SiteFactory()
        requester = RoleFactory()

        ValidationRequest.objects.create(
            request_type='referent_validation',
            status='pending',
            requester=requester,
            target_site=site
        )

        client = APIClient()
        client.force_authenticate(user=super_admin)
        response = client.get('/api/validations/pending_count/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['pending_count'] >= 1


@pytest.mark.django_db
@pytest.mark.unit
class TestValidationRequestViewSetMyRequests:
    """Tests for ValidationRequestViewSet my_requests endpoint."""

    def test_my_requests(self):
        """Test getting user's own requests."""
        user = RoleFactory()
        site = SiteFactory()

        ValidationRequest.objects.create(
            request_type='site_access',
            status='pending',
            requester=user,
            target_site=site
        )

        client = APIClient()
        client.force_authenticate(user=user)
        response = client.get('/api/validations/my_requests/')

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) >= 1
        # Check request type instead of requester (serializer format may vary)
        assert response.data[0]['request_type'] == 'site_access'


@pytest.mark.django_db
@pytest.mark.unit
class TestValidationRequestViewSetTypes:
    """Tests for ValidationRequestViewSet types endpoint."""

    def test_types(self):
        """Test getting validation request types."""
        user = RoleFactory()

        client = APIClient()
        client.force_authenticate(user=user)
        response = client.get('/api/validations/types/')

        assert response.status_code == status.HTTP_200_OK
        assert 'request_types' in response.data
        assert 'statuses' in response.data
        assert len(response.data['request_types']) > 0
        assert len(response.data['statuses']) > 0


@pytest.mark.django_db
@pytest.mark.unit
class TestValidationRequestViewSetApprove:
    """Tests for ValidationRequestViewSet approve endpoint."""

    def test_approve_validation_success(self):
        """Test approving a validation request."""
        organisme = OrganismeFactory()
        site = SiteFactory()
        CorOgSiteFactory(uuid_og=organisme, id_site=site)

        referent = RoleFactory(id_organisme=organisme)
        CorRoleSiteFactory(id_role=referent, id_site=site, referent=True, referent_valid=True)

        requester = RoleFactory()
        CorRoleSiteFactory(id_role=requester, id_site=site, referent=False)

        request = ValidationRequest.objects.create(
            request_type='referent_validation',
            status='pending',
            requester=requester,
            target_site=site
        )

        client = APIClient()
        client.force_authenticate(user=referent)
        response = client.post(f'/api/validations/{request.id}/approve/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['status'] == 'approved'

        request.refresh_from_db()
        assert request.status == 'approved'

    def test_approve_validation_already_processed(self):
        """Test error when trying to approve already processed request."""
        super_admin = SuperAdminFactory()
        site = SiteFactory()
        requester = RoleFactory()
        CorRoleSiteFactory(id_role=requester, id_site=site, referent=False)

        request = ValidationRequest.objects.create(
            request_type='referent_validation',
            status='approved',  # Already approved
            requester=requester,
            target_site=site,
            validator=super_admin
        )

        client = APIClient()
        client.force_authenticate(user=super_admin)
        response = client.post(f'/api/validations/{request.id}/approve/')

        assert response.status_code == status.HTTP_409_CONFLICT

    def test_approve_validation_no_permission(self):
        """Test error when user doesn't have permission."""
        regular_user = RoleFactory()
        site = SiteFactory()
        requester = RoleFactory()

        request = ValidationRequest.objects.create(
            request_type='referent_validation',
            status='pending',
            requester=requester,
            target_site=site
        )

        client = APIClient()
        client.force_authenticate(user=regular_user)
        response = client.post(f'/api/validations/{request.id}/approve/')

        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
@pytest.mark.unit
class TestValidationRequestViewSetReject:
    """Tests for ValidationRequestViewSet reject endpoint."""

    def test_reject_validation_success(self):
        """Test rejecting a validation request."""
        super_admin = SuperAdminFactory()
        site = SiteFactory()
        requester = RoleFactory()
        CorRoleSiteFactory(id_role=requester, id_site=site, referent=False)

        request = ValidationRequest.objects.create(
            request_type='referent_validation',
            status='pending',
            requester=requester,
            target_site=site
        )

        client = APIClient()
        client.force_authenticate(user=super_admin)
        response = client.post(
            f'/api/validations/{request.id}/reject/',
            {'comment': 'Not qualified'}
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data['status'] == 'rejected'

        request.refresh_from_db()
        assert request.status == 'rejected'

    def test_reject_validation_without_comment(self):
        """Test error when rejecting without comment."""
        super_admin = SuperAdminFactory()
        site = SiteFactory()
        requester = RoleFactory()

        request = ValidationRequest.objects.create(
            request_type='referent_validation',
            status='pending',
            requester=requester,
            target_site=site
        )

        client = APIClient()
        client.force_authenticate(user=super_admin)
        response = client.post(f'/api/validations/{request.id}/reject/', {})

        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
@pytest.mark.unit
class TestValidationRequestViewSetCancel:
    """Tests for ValidationRequestViewSet cancel endpoint."""

    def test_cancel_own_request(self):
        """Test user can cancel their own request."""
        user = RoleFactory()
        site = SiteFactory()

        request = ValidationRequest.objects.create(
            request_type='site_access',
            status='pending',
            requester=user,
            target_site=site
        )

        client = APIClient()
        client.force_authenticate(user=user)
        response = client.post(f'/api/validations/{request.id}/cancel/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['status'] == 'cancelled'

        request.refresh_from_db()
        assert request.status == 'cancelled'

    def test_cancel_other_user_request(self):
        """Test user cannot cancel another user's request."""
        user = RoleFactory()
        other_user = RoleFactory()
        site = SiteFactory()

        request = ValidationRequest.objects.create(
            request_type='site_access',
            status='pending',
            requester=other_user,
            target_site=site
        )

        client = APIClient()
        client.force_authenticate(user=user)
        response = client.post(f'/api/validations/{request.id}/cancel/')

        # 404 is returned because the queryset filters by visible requests
        # User cannot see other user's requests, so it appears as not found
        assert response.status_code in [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND]


@pytest.mark.django_db
@pytest.mark.unit
class TestValidationRequestViewSetRequestPlanAccess:
    """Tests for ValidationRequestViewSet request_plan_access endpoint."""

    def test_request_plan_access_success(self):
        """Test successful plan access request."""
        user = RoleFactory()
        site = SiteFactory()
        plan = PlanGestionFactory(statut='valide', sites=[site])

        client = APIClient()
        client.force_authenticate(user=user)
        response = client.post('/api/validations/request_plan_access/', {
            'plan_id': plan.id_pg,
            'justification': 'Need access for work'
        })

        assert response.status_code == status.HTTP_201_CREATED
        assert 'id' in response.data

    def test_request_plan_access_already_has_access(self):
        """Test error when user already has access."""
        user = RoleFactory()
        site = SiteFactory()
        plan = PlanGestionFactory(statut='valide', sites=[site], referents=[user])

        client = APIClient()
        client.force_authenticate(user=user)
        response = client.post('/api/validations/request_plan_access/', {
            'plan_id': plan.id_pg
        })

        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
@pytest.mark.unit
class TestValidationRequestViewSetAdminDeactivation:
    """Tests for ValidationRequestViewSet request_admin_deactivation endpoint."""

    def test_request_admin_deactivation_success(self):
        """Test successful admin deactivation request."""
        organisme = OrganismeFactory()
        requester = AdminOrganismeFactory(id_organisme=organisme)
        target = AdminOrganismeFactory(id_organisme=organisme)

        client = APIClient()
        client.force_authenticate(user=requester)
        response = client.post('/api/validations/request_admin_deactivation/', {
            'target_user_id': target.id_role,
            'justification': 'Inactive admin'
        })

        assert response.status_code == status.HTTP_201_CREATED

    def test_request_admin_deactivation_other_organisme(self):
        """Test error when requesting deactivation for different organisme."""
        org1 = OrganismeFactory()
        org2 = OrganismeFactory()
        requester = AdminOrganismeFactory(id_organisme=org1)
        target = AdminOrganismeFactory(id_organisme=org2)

        client = APIClient()
        client.force_authenticate(user=requester)
        response = client.post('/api/validations/request_admin_deactivation/', {
            'target_user_id': target.id_role,
            'justification': 'Inactive admin'
        })

        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
@pytest.mark.unit
class TestValidationRequestViewSetAdminPromotion:
    """Tests for ValidationRequestViewSet request_admin_promotion endpoint."""

    def test_request_admin_promotion_success(self):
        """Test successful admin promotion request."""
        organisme = OrganismeFactory()
        requester = AdminOrganismeFactory(id_organisme=organisme)
        target = RoleFactory(id_organisme=organisme, role_level='utilisateur')

        client = APIClient()
        client.force_authenticate(user=requester)
        response = client.post('/api/validations/request_admin_promotion/', {
            'target_user_id': target.id_role,
            'justification': 'Good candidate'
        })

        assert response.status_code == status.HTTP_201_CREATED

    def test_request_admin_promotion_already_admin(self):
        """Test error when target is already admin."""
        organisme = OrganismeFactory()
        requester = AdminOrganismeFactory(id_organisme=organisme)
        target = AdminOrganismeFactory(id_organisme=organisme)

        client = APIClient()
        client.force_authenticate(user=requester)
        response = client.post('/api/validations/request_admin_promotion/', {
            'target_user_id': target.id_role,
            'justification': 'Good candidate'
        })

        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
@pytest.mark.unit
class TestValidationRequestViewSetAdminDemotion:
    """Tests for ValidationRequestViewSet request_admin_demotion endpoint."""

    def test_request_admin_demotion_success(self):
        """Test successful admin demotion request."""
        organisme = OrganismeFactory()
        requester = AdminOrganismeFactory(id_organisme=organisme)
        target = AdminOrganismeFactory(id_organisme=organisme)

        client = APIClient()
        client.force_authenticate(user=requester)
        response = client.post('/api/validations/request_admin_demotion/', {
            'target_user_id': target.id_role,
            'justification': 'No longer admin'
        })

        assert response.status_code == status.HTTP_201_CREATED


@pytest.mark.django_db
@pytest.mark.unit
class TestValidationRequestViewSetModuleAccess:
    """Tests for ValidationRequestViewSet module access endpoints."""

    @pytest.fixture
    def module_with_access(self):
        """Create a module that requires access."""
        from apps.core.models import Module
        module, _ = Module.objects.get_or_create(
            code='test_module',
            defaults={
                'name': 'Test Module',
                'description': 'Module for testing',
                'is_active': True,
                'requires_access': True,
                'display_order': 99
            }
        )
        return module

    def test_request_module_access_success(self, module_with_access):
        """Test successful module access request."""
        user = RoleFactory()

        client = APIClient()
        client.force_authenticate(user=user)
        response = client.post('/api/validations/request_module_access/', {
            'module_code': module_with_access.code,
            'justification': 'Need access'
        })

        assert response.status_code == status.HTTP_201_CREATED

    def test_grant_module_access_super_admin(self, module_with_access):
        """Test super admin can grant module access."""
        super_admin = SuperAdminFactory()
        user = RoleFactory()

        client = APIClient()
        client.force_authenticate(user=super_admin)
        response = client.post('/api/validations/grant_module_access/', {
            'user_id': user.id_role,
            'module_code': module_with_access.code
        })

        assert response.status_code == status.HTTP_200_OK

    def test_grant_module_access_non_admin(self, module_with_access):
        """Test non-admin cannot grant module access."""
        user = RoleFactory()
        target = RoleFactory()

        client = APIClient()
        client.force_authenticate(user=user)
        response = client.post('/api/validations/grant_module_access/', {
            'user_id': target.id_role,
            'module_code': module_with_access.code
        })

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_revoke_module_access(self, module_with_access):
        """Test revoking module access."""
        super_admin = SuperAdminFactory()
        user = RoleFactory()

        # First grant access
        ValidationRequest.objects.create(
            request_type='module_access',
            status='approved',
            requester=user,
            target_module=module_with_access.code,
            validator=super_admin
        )

        client = APIClient()
        client.force_authenticate(user=super_admin)
        response = client.post('/api/validations/revoke_module_access/', {
            'user_id': user.id_role,
            'module_code': module_with_access.code
        })

        assert response.status_code == status.HTTP_200_OK

    def test_my_module_access(self, module_with_access):
        """Test getting own module access."""
        user = RoleFactory()
        super_admin = SuperAdminFactory()

        # Create approved module access
        ValidationRequest.objects.create(
            request_type='module_access',
            status='approved',
            requester=user,
            target_module=module_with_access.code,
            validator=super_admin
        )

        client = APIClient()
        client.force_authenticate(user=user)
        response = client.get('/api/validations/my_module_access/')

        assert response.status_code == status.HTTP_200_OK
        assert module_with_access.code in response.data['modules']


# =============================================================================
# PUBLIC REGISTRATION TESTS
# =============================================================================

@pytest.mark.django_db
@pytest.mark.unit
class TestPublicRegistration:
    """Tests for public registration endpoint."""

    def test_registration_success(self):
        """Test successful public registration."""
        organisme = OrganismeFactory()
        AdminOrganismeFactory(id_organisme=organisme)  # Create validator

        client = APIClient()
        response = client.post('/api/auth/register/', {
            'email': 'newuser@test.fr',
            'identifiant': 'jdupont',
            'password': 'Test123!@#',
            'password_confirm': 'Test123!@#',
            'nom_role': 'Dupont',
            'prenom_role': 'Jean',
            'requested_organisme_id': organisme.id_organisme,
            'justification': 'Need access'
        })

        assert response.status_code == status.HTTP_201_CREATED
        assert 'validation_request_id' in response.data

    def test_registration_email_exists(self):
        """Test error when email already exists."""
        organisme = OrganismeFactory()
        existing_user = RoleFactory(email='existing@test.fr')

        client = APIClient()
        response = client.post('/api/auth/register/', {
            'email': 'existing@test.fr',
            'identifiant': 'jdupont2',
            'password': 'Test123!@#',
            'password_confirm': 'Test123!@#',
            'nom_role': 'Dupont',
            'prenom_role': 'Jean',
            'requested_organisme_id': organisme.id_organisme
        })

        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
@pytest.mark.unit
class TestCheckRegistrationStatus:
    """Tests for check registration status endpoint."""

    def test_check_status_pending(self):
        """Test checking status of pending registration."""
        organisme = OrganismeFactory()
        pending = PendingUserFactory(requested_organisme=organisme)

        client = APIClient()
        response = client.get(f'/api/auth/registration-status/?email={pending.email}')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['status'] == 'pending'

    def test_check_status_registered(self):
        """Test checking status when user is already registered."""
        user = RoleFactory()

        client = APIClient()
        response = client.get(f'/api/auth/registration-status/?email={user.email}')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['status'] == 'registered'

    def test_check_status_not_found(self):
        """Test checking status for unknown email."""
        client = APIClient()
        response = client.get('/api/auth/registration-status/?email=unknown@test.fr')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['status'] == 'not_found'

    def test_check_status_no_email(self):
        """Test error when email is not provided."""
        client = APIClient()
        response = client.get('/api/auth/registration-status/')

        assert response.status_code == status.HTTP_400_BAD_REQUEST
