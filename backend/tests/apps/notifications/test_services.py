"""
Unit tests for notifications app services.
Tests ValidationService and NotificationService.
"""
import pytest
from django.utils import timezone

from apps.notifications.models import ValidationRequest, Notification
from apps.notifications.services import ValidationService, NotificationService
from apps.users.models import CorRoleSite
from tests.factories.users import (
    RoleFactory, SuperAdminFactory, AdminOrganismeFactory,
    SiteFactory, OrganismeFactory, CorRoleSiteFactory, CorOgSiteFactory
)
from tests.factories.notifications import (
    ReferentValidationRequestFactory,
    ValidationRequestFactory
)


# =============================================================================
# VALIDATION SERVICE TESTS
# =============================================================================

@pytest.mark.django_db
@pytest.mark.unit
class TestValidationServiceCanValidate:
    """Tests for ValidationService.can_validate_request method."""

    def test_super_admin_can_validate(self):
        """Test super admin can validate any request."""
        super_admin = SuperAdminFactory()
        request = ReferentValidationRequestFactory()

        result = ValidationService.can_validate_request(super_admin, request)
        assert result is True

    def test_admin_og_can_validate_own_site_request(self):
        """Test admin organisme can validate requests for sites of their org."""
        organisme = OrganismeFactory()
        admin_og = AdminOrganismeFactory(id_organisme=organisme)
        site = SiteFactory()
        CorOgSiteFactory(uuid_og=organisme, id_site=site)

        requester = RoleFactory()
        CorRoleSiteFactory(id_role=requester, id_site=site, referent=False)

        request = ValidationRequest.objects.create(
            request_type='referent_validation',
            status='pending',
            requester=requester,
            target_site=site
        )

        result = ValidationService.can_validate_request(admin_og, request)
        assert result is True

    def test_admin_og_cannot_validate_other_org_site_request(self):
        """Test admin organisme cannot validate requests for other org's sites."""
        org1 = OrganismeFactory()
        org2 = OrganismeFactory()
        admin_og = AdminOrganismeFactory(id_organisme=org1)
        site = SiteFactory()
        CorOgSiteFactory(uuid_og=org2, id_site=site)  # Site belongs to org2

        requester = RoleFactory()
        CorRoleSiteFactory(id_role=requester, id_site=site, referent=False)

        request = ValidationRequest.objects.create(
            request_type='referent_validation',
            status='pending',
            requester=requester,
            target_site=site
        )

        result = ValidationService.can_validate_request(admin_og, request)
        assert result is False

    def test_referent_can_validate_own_site_request(self):
        """Test referent can validate requests for their site."""
        site = SiteFactory()
        referent = RoleFactory()
        CorRoleSiteFactory(id_role=referent, id_site=site, referent=True, referent_valid=True)

        requester = RoleFactory()
        CorRoleSiteFactory(id_role=requester, id_site=site, referent=False)

        request = ValidationRequest.objects.create(
            request_type='referent_validation',
            status='pending',
            requester=requester,
            target_site=site
        )

        result = ValidationService.can_validate_request(referent, request)
        assert result is True

    def test_referent_cannot_validate_other_site_request(self):
        """Test referent cannot validate requests for other sites."""
        site1 = SiteFactory()
        site2 = SiteFactory()
        referent = RoleFactory()
        CorRoleSiteFactory(id_role=referent, id_site=site1, referent=True, referent_valid=True)

        requester = RoleFactory()
        CorRoleSiteFactory(id_role=requester, id_site=site2, referent=False)

        request = ValidationRequest.objects.create(
            request_type='referent_validation',
            status='pending',
            requester=requester,
            target_site=site2
        )

        result = ValidationService.can_validate_request(referent, request)
        assert result is False

    def test_regular_user_cannot_validate(self):
        """Test regular user cannot validate any request."""
        user = RoleFactory()
        request = ReferentValidationRequestFactory()

        result = ValidationService.can_validate_request(user, request)
        assert result is False


@pytest.mark.django_db
@pytest.mark.unit
class TestValidationServiceApproveReferent:
    """Tests for ValidationService.approve_referent_validation method."""

    def test_approve_referent_validation_success(self):
        """Test successful referent validation approval."""
        site = SiteFactory()
        requester = RoleFactory()
        validator = SuperAdminFactory()
        CorRoleSiteFactory(id_role=requester, id_site=site, referent=False, referent_valid=False)

        request = ValidationRequest.objects.create(
            request_type='referent_validation',
            status='pending',
            requester=requester,
            target_site=site
        )

        ValidationService.approve_referent_validation(request, validator, 'Approved')

        # Check request status
        request.refresh_from_db()
        assert request.status == 'approved'
        assert request.validator == validator

        # Check user is now referent
        cor_role_site = CorRoleSite.objects.get(id_role=requester, id_site=site)
        assert cor_role_site.referent is True
        assert cor_role_site.referent_valid is True

    def test_approve_referent_validation_wrong_type(self):
        """Test error when trying to approve non-referent request as referent."""
        request = ValidationRequestFactory(request_type='site_access', status='pending')
        validator = SuperAdminFactory()

        with pytest.raises(ValueError) as exc_info:
            ValidationService.approve_referent_validation(request, validator)

        assert 'referent' in str(exc_info.value).lower()

    def test_approve_referent_validation_no_site(self):
        """Test error when request has no target site."""
        requester = RoleFactory()
        validator = SuperAdminFactory()

        request = ValidationRequest.objects.create(
            request_type='referent_validation',
            status='pending',
            requester=requester,
            target_site=None
        )

        with pytest.raises(ValueError) as exc_info:
            ValidationService.approve_referent_validation(request, validator)

        assert 'manquant' in str(exc_info.value).lower()

    def test_approve_referent_validation_user_not_linked(self):
        """Test error when user is not linked to site."""
        site = SiteFactory()
        requester = RoleFactory()
        validator = SuperAdminFactory()
        # No CorRoleSite created

        request = ValidationRequest.objects.create(
            request_type='referent_validation',
            status='pending',
            requester=requester,
            target_site=site
        )

        with pytest.raises(ValueError) as exc_info:
            ValidationService.approve_referent_validation(request, validator)

        assert 'lie' in str(exc_info.value).lower()


@pytest.mark.django_db
@pytest.mark.unit
class TestValidationServiceReject:
    """Tests for ValidationService.reject_request method."""

    def test_reject_request_success(self):
        """Test successful request rejection."""
        site = SiteFactory()
        requester = RoleFactory()
        validator = SuperAdminFactory()
        CorRoleSiteFactory(id_role=requester, id_site=site, referent=False)

        request = ValidationRequest.objects.create(
            request_type='referent_validation',
            status='pending',
            requester=requester,
            target_site=site
        )

        ValidationService.reject_request(request, validator, 'Rejected for testing')

        request.refresh_from_db()
        assert request.status == 'rejected'
        assert request.validator == validator
        assert request.validation_comment == 'Rejected for testing'

        # Verify user is NOT referent
        cor_role_site = CorRoleSite.objects.get(id_role=requester, id_site=site)
        assert cor_role_site.referent is False


@pytest.mark.django_db
@pytest.mark.unit
class TestValidationServiceGetPendingRequests:
    """Tests for ValidationService.get_pending_requests_for_user method."""

    def test_super_admin_sees_all_pending(self):
        """Test super admin sees all pending requests."""
        super_admin = SuperAdminFactory()
        site1 = SiteFactory()
        site2 = SiteFactory()

        requester1 = RoleFactory()
        requester2 = RoleFactory()
        CorRoleSiteFactory(id_role=requester1, id_site=site1, referent=False)
        CorRoleSiteFactory(id_role=requester2, id_site=site2, referent=False)

        ValidationRequest.objects.create(
            request_type='referent_validation', status='pending',
            requester=requester1, target_site=site1
        )
        ValidationRequest.objects.create(
            request_type='referent_validation', status='pending',
            requester=requester2, target_site=site2
        )

        pending = ValidationService.get_pending_requests_for_user(super_admin)
        assert pending.count() >= 2

    def test_admin_og_sees_own_site_pending(self):
        """Test admin organisme sees pending requests for their sites."""
        organisme = OrganismeFactory()
        admin_og = AdminOrganismeFactory(id_organisme=organisme)
        site = SiteFactory()
        CorOgSiteFactory(uuid_og=organisme, id_site=site)

        requester = RoleFactory()
        CorRoleSiteFactory(id_role=requester, id_site=site, referent=False)

        ValidationRequest.objects.create(
            request_type='referent_validation', status='pending',
            requester=requester, target_site=site
        )

        pending = ValidationService.get_pending_requests_for_user(admin_og)
        assert pending.count() >= 1

    def test_referent_sees_own_site_pending(self):
        """Test referent sees pending requests for their site."""
        site = SiteFactory()
        referent = RoleFactory()
        CorRoleSiteFactory(id_role=referent, id_site=site, referent=True, referent_valid=True)

        requester = RoleFactory()
        CorRoleSiteFactory(id_role=requester, id_site=site, referent=False)

        ValidationRequest.objects.create(
            request_type='referent_validation', status='pending',
            requester=requester, target_site=site
        )

        pending = ValidationService.get_pending_requests_for_user(referent)
        assert pending.count() >= 1

    def test_regular_user_sees_nothing(self):
        """Test regular user sees no pending requests."""
        user = RoleFactory()
        ReferentValidationRequestFactory()

        pending = ValidationService.get_pending_requests_for_user(user)
        assert pending.count() == 0


@pytest.mark.django_db
@pytest.mark.unit
class TestValidationServiceGetValidators:
    """Tests for ValidationService.get_validators_for_request method."""

    def test_get_validators_for_referent_request(self):
        """Test getting validators for referent request."""
        organisme = OrganismeFactory()
        site = SiteFactory()
        CorOgSiteFactory(uuid_og=organisme, id_site=site)

        # Create existing referent
        existing_referent = RoleFactory(id_organisme=organisme)
        CorRoleSiteFactory(
            id_role=existing_referent, id_site=site,
            referent=True, referent_valid=True
        )

        # Create admin organisme
        admin_og = AdminOrganismeFactory(id_organisme=organisme)

        requester = RoleFactory()
        CorRoleSiteFactory(id_role=requester, id_site=site, referent=False)

        request = ValidationRequest.objects.create(
            request_type='referent_validation',
            status='pending',
            requester=requester,
            target_site=site
        )

        validators = ValidationService.get_validators_for_request(request)

        # Handle both QuerySet and set return types
        if hasattr(validators, 'values_list'):
            validator_ids = list(validators.values_list('id_role', flat=True))
        else:
            # It's a set of Role objects
            validator_ids = [v.id_role for v in validators]

        # Should include existing referent
        assert existing_referent.id_role in validator_ids


# =============================================================================
# NOTIFICATION SERVICE TESTS
# =============================================================================

@pytest.mark.django_db
@pytest.mark.unit
class TestNotificationServiceCreate:
    """Tests for NotificationService.create_notification method."""

    def test_create_notification(self):
        """Test creating a notification via service."""
        user = RoleFactory()

        notification = NotificationService.create_notification(
            recipient=user,
            notification_type='info',
            title='Test Notification',
            message='This is a test.'
        )

        assert notification is not None
        assert notification.recipient == user
        assert notification.title == 'Test Notification'
        assert notification.read is False

    def test_create_notification_with_related_objects(self):
        """Test creating notification with related objects."""
        user = RoleFactory()
        site = SiteFactory()
        related_user = RoleFactory()

        notification = NotificationService.create_notification(
            recipient=user,
            notification_type='validation_request',
            title='New Request',
            message='A new request has been made.',
            related_site=site,
            related_user=related_user
        )

        assert notification.related_site == site
        assert notification.related_user == related_user


@pytest.mark.django_db
@pytest.mark.unit
class TestNotificationServiceNotifyValidators:
    """Tests for NotificationService.notify_validators method."""

    def test_notify_validators_creates_notifications(self):
        """Test that notify_validators creates notifications for validators."""
        organisme = OrganismeFactory()
        site = SiteFactory()
        CorOgSiteFactory(uuid_og=organisme, id_site=site)

        # Create validator (existing referent)
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

        NotificationService.notify_validators(request)

        # Check notification was created for referent
        notifications = Notification.objects.filter(
            recipient=referent,
            notification_type='validation_request'
        )
        assert notifications.exists()


@pytest.mark.django_db
@pytest.mark.unit
class TestNotificationServiceNotifyResult:
    """Tests for NotificationService.notify_validation_result method."""

    def test_notify_validation_approved(self):
        """Test notification sent when request is approved."""
        site = SiteFactory()
        requester = RoleFactory()
        validator = SuperAdminFactory()
        CorRoleSiteFactory(id_role=requester, id_site=site, referent=False)

        request = ValidationRequest.objects.create(
            request_type='referent_validation',
            status='approved',
            requester=requester,
            target_site=site,
            validator=validator
        )

        NotificationService.notify_validation_result(request, approved=True)

        notifications = Notification.objects.filter(
            recipient=requester,
            notification_type='validation_approved'
        )
        assert notifications.exists()

    def test_notify_validation_rejected(self):
        """Test notification sent when request is rejected."""
        site = SiteFactory()
        requester = RoleFactory()
        validator = SuperAdminFactory()
        CorRoleSiteFactory(id_role=requester, id_site=site, referent=False)

        request = ValidationRequest.objects.create(
            request_type='referent_validation',
            status='rejected',
            requester=requester,
            target_site=site,
            validator=validator,
            validation_comment='Not qualified'
        )

        NotificationService.notify_validation_result(request, approved=False)

        notifications = Notification.objects.filter(
            recipient=requester,
            notification_type='validation_rejected'
        )
        assert notifications.exists()
