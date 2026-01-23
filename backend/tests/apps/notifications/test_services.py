"""
Unit tests for notifications app services.
Tests ValidationService and NotificationService.
"""
import pytest
from django.utils import timezone

from apps.notifications.models import ValidationRequest, Notification
from apps.notifications.services import ValidationService, NotificationService
from apps.users.models import CorRoleSite, CorOgSite
from tests.factories.users import (
    RoleFactory, SuperAdminFactory, AdminOrganismeFactory,
    SiteFactory, OrganismeFactory, CorRoleSiteFactory, CorOgSiteFactory
)
from tests.factories.plans import PlanGestionFactory
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


# =============================================================================
# ADDITIONAL NOTIFICATION SERVICE TESTS
# =============================================================================

@pytest.mark.django_db
@pytest.mark.unit
class TestNotificationServiceBuildMessage:
    """Tests for NotificationService._build_validation_message method."""

    def test_build_message_user_registration(self):
        """Test message for user registration request."""
        from apps.notifications.models import PendingUser
        organisme = OrganismeFactory()
        request = ValidationRequest.objects.create(
            request_type='user_registration',
            status='pending',
            requested_organisme=organisme
        )
        pending = PendingUser.objects.create(
            email='newuser@test.fr',
            nom_role='Dupont',
            prenom_role='Jean',
            requested_organisme=organisme,
            password_hash='hash',
            validation_request=request
        )

        message = NotificationService._build_validation_message(request)
        assert 'Jean Dupont' in message
        assert 'newuser@test.fr' in message

    def test_build_message_site_access(self):
        """Test message for site access request."""
        site = SiteFactory()
        requester = RoleFactory()
        request = ValidationRequest.objects.create(
            request_type='site_access',
            status='pending',
            requester=requester,
            target_site=site
        )

        message = NotificationService._build_validation_message(request)
        assert site.nom_site in message
        assert 'acces' in message.lower()

    def test_build_message_admin_promotion(self):
        """Test message for admin promotion request."""
        requester = RoleFactory()
        target = RoleFactory()
        request = ValidationRequest.objects.create(
            request_type='admin_promotion',
            status='pending',
            requester=requester,
            target_user=target
        )

        message = NotificationService._build_validation_message(request)
        assert 'promotion' in message.lower()

    def test_build_message_admin_demotion(self):
        """Test message for admin demotion request."""
        requester = RoleFactory()
        target = RoleFactory()
        request = ValidationRequest.objects.create(
            request_type='admin_demotion',
            status='pending',
            requester=requester,
            target_user=target
        )

        message = NotificationService._build_validation_message(request)
        assert 'retrogradation' in message.lower()

    def test_build_message_site_org_link(self):
        """Test message for site-org link request."""
        site = SiteFactory()
        organisme = OrganismeFactory()
        requester = RoleFactory()
        request = ValidationRequest.objects.create(
            request_type='site_org_link',
            status='pending',
            requester=requester,
            target_site=site,
            requested_organisme=organisme
        )

        message = NotificationService._build_validation_message(request)
        assert site.nom_site in message
        assert 'lier' in message.lower()

    def test_build_message_site_org_unlink(self):
        """Test message for site-org unlink request."""
        site = SiteFactory()
        organisme = OrganismeFactory()
        requester = RoleFactory()
        request = ValidationRequest.objects.create(
            request_type='site_org_unlink',
            status='pending',
            requester=requester,
            target_site=site,
            requested_organisme=organisme
        )

        message = NotificationService._build_validation_message(request)
        assert site.nom_site in message
        assert 'retirer' in message.lower()

    def test_build_message_site_creation(self):
        """Test message for site creation request."""
        site = SiteFactory(active=False)
        requester = RoleFactory()
        request = ValidationRequest.objects.create(
            request_type='site_creation',
            status='pending',
            requester=requester,
            target_site=site
        )

        message = NotificationService._build_validation_message(request)
        assert site.nom_site in message
        assert 'cree' in message.lower() or 'validation' in message.lower()

    def test_build_message_invite_org_to_site(self):
        """Test message for invite org to site request."""
        site = SiteFactory()
        organisme = OrganismeFactory()
        requester = RoleFactory()
        request = ValidationRequest.objects.create(
            request_type='invite_org_to_site',
            status='pending',
            requester=requester,
            target_site=site,
            requested_organisme=organisme
        )

        message = NotificationService._build_validation_message(request)
        assert 'invite' in message.lower()

    def test_build_message_invite_user_to_site(self):
        """Test message for invite user to site request."""
        site = SiteFactory()
        requester = RoleFactory()
        target_user = RoleFactory()
        request = ValidationRequest.objects.create(
            request_type='invite_user_to_site',
            status='pending',
            requester=requester,
            target_site=site,
            target_user=target_user
        )

        message = NotificationService._build_validation_message(request)
        assert 'invite' in message.lower()


@pytest.mark.django_db
@pytest.mark.unit
class TestNotificationServiceNotifyOtherValidators:
    """Tests for NotificationService.notify_other_validators method."""

    def test_notify_other_validators_creates_notifications(self):
        """Test that other validators are notified when request is processed."""
        organisme = OrganismeFactory()
        site = SiteFactory()
        CorOgSiteFactory(uuid_og=organisme, id_site=site)

        # Create two validators
        referent1 = RoleFactory(id_organisme=organisme)
        CorRoleSiteFactory(id_role=referent1, id_site=site, referent=True, referent_valid=True)
        referent2 = RoleFactory(id_organisme=organisme)
        CorRoleSiteFactory(id_role=referent2, id_site=site, referent=True, referent_valid=True)

        requester = RoleFactory()
        CorRoleSiteFactory(id_role=requester, id_site=site, referent=False)

        request = ValidationRequest.objects.create(
            request_type='referent_validation',
            status='approved',
            requester=requester,
            target_site=site,
            validator=referent1
        )

        # referent1 processed it, referent2 should be notified
        NotificationService.notify_other_validators(request, referent1, approved=True)

        # Check notification was created for referent2
        notifications = Notification.objects.filter(
            recipient=referent2,
            notification_type='info'
        )
        assert notifications.exists()
        assert 'approuvee' in notifications.first().title.lower()

    def test_notify_other_validators_marks_old_notifications_as_read(self):
        """Test that old validation_request notifications are marked as read."""
        organisme = OrganismeFactory()
        site = SiteFactory()
        CorOgSiteFactory(uuid_og=organisme, id_site=site)

        referent1 = RoleFactory(id_organisme=organisme)
        CorRoleSiteFactory(id_role=referent1, id_site=site, referent=True, referent_valid=True)
        referent2 = RoleFactory(id_organisme=organisme)
        CorRoleSiteFactory(id_role=referent2, id_site=site, referent=True, referent_valid=True)

        requester = RoleFactory()
        CorRoleSiteFactory(id_role=requester, id_site=site, referent=False)

        request = ValidationRequest.objects.create(
            request_type='referent_validation',
            status='pending',
            requester=requester,
            target_site=site
        )

        # Create old notification for referent2
        old_notif = Notification.objects.create(
            recipient=referent2,
            notification_type='validation_request',
            title='Old notification',
            message='Test',
            related_validation=request,
            read=False
        )

        request.status = 'approved'
        request.validator = referent1
        request.save()

        NotificationService.notify_other_validators(request, referent1, approved=True)

        old_notif.refresh_from_db()
        assert old_notif.read is True


@pytest.mark.django_db
@pytest.mark.unit
class TestNotificationServiceNotifySuperAdmins:
    """Tests for NotificationService.notify_super_admins method."""

    def test_notify_super_admins(self):
        """Test notifying all super admins."""
        super_admin1 = SuperAdminFactory()
        super_admin2 = SuperAdminFactory()

        NotificationService.notify_super_admins(
            notification_type='system_alert',
            title='System Alert',
            message='This is a test alert.'
        )

        notifs1 = Notification.objects.filter(recipient=super_admin1, title='System Alert')
        notifs2 = Notification.objects.filter(recipient=super_admin2, title='System Alert')

        assert notifs1.exists()
        assert notifs2.exists()


@pytest.mark.django_db
@pytest.mark.unit
class TestNotificationServiceNotifySiteOrphaned:
    """Tests for NotificationService.notify_site_orphaned method."""

    def test_notify_site_orphaned(self):
        """Test notification when site has no users."""
        site = SiteFactory()
        super_admin = SuperAdminFactory()

        NotificationService.notify_site_orphaned(site)

        notifs = Notification.objects.filter(
            recipient=super_admin,
            notification_type='site_orphaned'
        )
        assert notifs.exists()
        assert site.nom_site in notifs.first().title


@pytest.mark.django_db
@pytest.mark.unit
class TestNotificationServiceNotifyOrganismeNoAdmin:
    """Tests for NotificationService.notify_organisme_no_admin method."""

    def test_notify_organisme_no_admin(self):
        """Test notification when organisme has no admin."""
        organisme = OrganismeFactory()
        super_admin = SuperAdminFactory()

        NotificationService.notify_organisme_no_admin(organisme)

        notifs = Notification.objects.filter(
            recipient=super_admin,
            notification_type='organisme_no_admin'
        )
        assert notifs.exists()
        assert organisme.nom_organisme in notifs.first().title


@pytest.mark.django_db
@pytest.mark.unit
class TestNotificationServiceNotifyUserDeactivated:
    """Tests for NotificationService.notify_user_deactivated method."""

    def test_notify_user_deactivated(self):
        """Test notification when user is deactivated."""
        user = RoleFactory()
        admin = SuperAdminFactory()

        NotificationService.notify_user_deactivated(user, admin, reason='Inactive')

        # User should receive notification
        user_notifs = Notification.objects.filter(
            recipient=user,
            notification_type='account_deactivated'
        )
        assert user_notifs.exists()
        assert 'Inactive' in user_notifs.first().message

        # Super admin should also be notified
        admin_notifs = Notification.objects.filter(
            recipient=admin,
            notification_type='account_deactivated'
        )
        assert admin_notifs.exists()


# =============================================================================
# ADDITIONAL VALIDATION SERVICE TESTS
# =============================================================================

@pytest.mark.django_db
@pytest.mark.unit
class TestValidationServiceGetAllRequests:
    """Tests for ValidationService.get_all_requests_for_user method."""

    def test_super_admin_sees_all_requests(self):
        """Test super admin sees all requests (pending and processed)."""
        super_admin = SuperAdminFactory()
        site = SiteFactory()

        requester = RoleFactory()
        CorRoleSiteFactory(id_role=requester, id_site=site, referent=False)

        # Create pending and approved requests
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

        all_requests = ValidationService.get_all_requests_for_user(super_admin)
        assert all_requests.count() >= 2

    def test_admin_og_sees_validated_requests(self):
        """Test admin organisme sees requests they validated."""
        organisme = OrganismeFactory()
        admin_og = AdminOrganismeFactory(id_organisme=organisme)
        site = SiteFactory()
        CorOgSiteFactory(uuid_og=organisme, id_site=site)

        requester = RoleFactory()
        CorRoleSiteFactory(id_role=requester, id_site=site, referent=False)

        # Create a request validated by this admin
        ValidationRequest.objects.create(
            request_type='referent_validation',
            status='approved',
            requester=requester,
            target_site=site,
            validator=admin_og
        )

        all_requests = ValidationService.get_all_requests_for_user(admin_og)
        assert all_requests.count() >= 1


@pytest.mark.django_db
@pytest.mark.unit
class TestValidationServiceApproveSiteAccess:
    """Tests for ValidationService.approve_site_access method."""

    def test_approve_site_access_success(self):
        """Test successful site access approval."""
        site = SiteFactory()
        requester = RoleFactory()
        validator = SuperAdminFactory()

        request = ValidationRequest.objects.create(
            request_type='site_access',
            status='pending',
            requester=requester,
            target_site=site,
            request_as_referent=False
        )

        ValidationService.approve_site_access(request, validator, 'Approved')

        request.refresh_from_db()
        assert request.status == 'approved'

        # Check user is linked to site
        cor = CorRoleSite.objects.get(id_role=requester, id_site=site)
        assert cor.referent is False

    def test_approve_site_access_as_referent(self):
        """Test site access approval with referent flag."""
        site = SiteFactory()
        requester = RoleFactory()
        validator = SuperAdminFactory()

        request = ValidationRequest.objects.create(
            request_type='site_access',
            status='pending',
            requester=requester,
            target_site=site,
            request_as_referent=True
        )

        ValidationService.approve_site_access(request, validator)

        cor = CorRoleSite.objects.get(id_role=requester, id_site=site)
        assert cor.referent is True
        assert cor.referent_valid is True

    def test_approve_site_access_wrong_type(self):
        """Test error when trying to approve wrong request type."""
        request = ValidationRequestFactory(request_type='referent_validation', status='pending')
        validator = SuperAdminFactory()

        with pytest.raises(ValueError) as exc_info:
            ValidationService.approve_site_access(request, validator)

        assert 'acces site' in str(exc_info.value).lower()


@pytest.mark.django_db
@pytest.mark.unit
class TestValidationServiceApproveSiteOrgLink:
    """Tests for ValidationService.approve_site_org_link method."""

    def test_approve_site_org_link_success(self):
        """Test successful site-org link approval."""
        site = SiteFactory()
        organisme = OrganismeFactory()
        requester = RoleFactory()
        validator = SuperAdminFactory()

        request = ValidationRequest.objects.create(
            request_type='site_org_link',
            status='pending',
            requester=requester,
            target_site=site,
            requested_organisme=organisme
        )

        ValidationService.approve_site_org_link(request, validator)

        request.refresh_from_db()
        assert request.status == 'approved'

        # Check link was created
        assert CorOgSite.objects.filter(id_site=site, uuid_og=organisme).exists()

    def test_approve_site_org_link_wrong_type(self):
        """Test error when trying to approve wrong request type."""
        request = ValidationRequestFactory(request_type='site_access', status='pending')
        validator = SuperAdminFactory()

        with pytest.raises(ValueError):
            ValidationService.approve_site_org_link(request, validator)


@pytest.mark.django_db
@pytest.mark.unit
class TestValidationServiceApproveSiteOrgUnlink:
    """Tests for ValidationService.approve_site_org_unlink method."""

    def test_approve_site_org_unlink_success(self):
        """Test successful site-org unlink approval."""
        site = SiteFactory()
        organisme = OrganismeFactory()
        CorOgSiteFactory(id_site=site, uuid_og=organisme)
        requester = RoleFactory()
        validator = SuperAdminFactory()

        request = ValidationRequest.objects.create(
            request_type='site_org_unlink',
            status='pending',
            requester=requester,
            target_site=site,
            requested_organisme=organisme
        )

        ValidationService.approve_site_org_unlink(request, validator)

        request.refresh_from_db()
        assert request.status == 'approved'

        # Check link was removed
        assert not CorOgSite.objects.filter(id_site=site, uuid_og=organisme).exists()

    def test_approve_site_org_unlink_link_not_exists(self):
        """Test approval when link doesn't exist anymore."""
        site = SiteFactory()
        organisme = OrganismeFactory()
        requester = RoleFactory()
        validator = SuperAdminFactory()

        request = ValidationRequest.objects.create(
            request_type='site_org_unlink',
            status='pending',
            requester=requester,
            target_site=site,
            requested_organisme=organisme
        )

        # Should not raise, just continue
        ValidationService.approve_site_org_unlink(request, validator)
        request.refresh_from_db()
        assert request.status == 'approved'


@pytest.mark.django_db
@pytest.mark.unit
class TestValidationServiceApproveSiteCreation:
    """Tests for ValidationService.approve_site_creation method."""

    def test_approve_site_creation_success(self):
        """Test successful site creation approval."""
        organisme = OrganismeFactory()
        requester = RoleFactory(id_organisme=organisme)
        site = SiteFactory(active=False)
        validator = SuperAdminFactory()

        request = ValidationRequest.objects.create(
            request_type='site_creation',
            status='pending',
            requester=requester,
            target_site=site,
            request_as_referent=True
        )

        ValidationService.approve_site_creation(request, validator)

        request.refresh_from_db()
        assert request.status == 'approved'

        site.refresh_from_db()
        assert site.active is True

        # Check user is linked as referent
        cor = CorRoleSite.objects.get(id_role=requester, id_site=site)
        assert cor.referent is True

        # Check organisme is linked
        assert CorOgSite.objects.filter(id_site=site, uuid_og=organisme).exists()

    def test_approve_site_creation_wrong_type(self):
        """Test error when trying to approve wrong request type."""
        request = ValidationRequestFactory(request_type='site_access', status='pending')
        validator = SuperAdminFactory()

        with pytest.raises(ValueError):
            ValidationService.approve_site_creation(request, validator)


@pytest.mark.django_db
@pytest.mark.unit
class TestValidationServiceApproveAdminPromotion:
    """Tests for ValidationService.approve_admin_promotion method."""

    def test_approve_admin_promotion_success(self):
        """Test successful admin promotion."""
        organisme = OrganismeFactory()
        requester = RoleFactory(id_organisme=organisme, role_level='admin_og')
        target = RoleFactory(id_organisme=organisme, role_level='utilisateur')
        validator = SuperAdminFactory()

        request = ValidationRequest.objects.create(
            request_type='admin_promotion',
            status='pending',
            requester=requester,
            target_user=target
        )

        ValidationService.approve_admin_promotion(request, validator)

        request.refresh_from_db()
        assert request.status == 'approved'

        target.refresh_from_db()
        assert target.role_level == 'admin_og'

    def test_approve_admin_promotion_non_super_admin_fails(self):
        """Test that non super admin cannot approve promotion."""
        organisme = OrganismeFactory()
        requester = RoleFactory(id_organisme=organisme, role_level='admin_og')
        target = RoleFactory(id_organisme=organisme, role_level='utilisateur')
        validator = AdminOrganismeFactory()

        request = ValidationRequest.objects.create(
            request_type='admin_promotion',
            status='pending',
            requester=requester,
            target_user=target
        )

        with pytest.raises(ValueError) as exc_info:
            ValidationService.approve_admin_promotion(request, validator)

        assert 'super administrateur' in str(exc_info.value).lower()

    def test_approve_admin_promotion_wrong_role_level(self):
        """Test error when target is not utilisateur."""
        organisme = OrganismeFactory()
        requester = RoleFactory(id_organisme=organisme, role_level='admin_og')
        target = RoleFactory(id_organisme=organisme, role_level='admin_og')
        validator = SuperAdminFactory()

        request = ValidationRequest.objects.create(
            request_type='admin_promotion',
            status='pending',
            requester=requester,
            target_user=target
        )

        with pytest.raises(ValueError) as exc_info:
            ValidationService.approve_admin_promotion(request, validator)

        assert 'utilisateur simple' in str(exc_info.value).lower()


@pytest.mark.django_db
@pytest.mark.unit
class TestValidationServiceApproveAdminDemotion:
    """Tests for ValidationService.approve_admin_demotion method."""

    def test_approve_admin_demotion_success(self):
        """Test successful admin demotion."""
        organisme = OrganismeFactory()
        requester = SuperAdminFactory()
        target = AdminOrganismeFactory(id_organisme=organisme)
        validator = SuperAdminFactory()

        request = ValidationRequest.objects.create(
            request_type='admin_demotion',
            status='pending',
            requester=requester,
            target_user=target
        )

        ValidationService.approve_admin_demotion(request, validator)

        request.refresh_from_db()
        assert request.status == 'approved'

        target.refresh_from_db()
        assert target.role_level == 'utilisateur'

    def test_approve_admin_demotion_wrong_role_level(self):
        """Test error when target is not admin_og."""
        target = RoleFactory(role_level='utilisateur')
        requester = SuperAdminFactory()
        validator = SuperAdminFactory()

        request = ValidationRequest.objects.create(
            request_type='admin_demotion',
            status='pending',
            requester=requester,
            target_user=target
        )

        with pytest.raises(ValueError) as exc_info:
            ValidationService.approve_admin_demotion(request, validator)

        assert 'admin_og' in str(exc_info.value).lower()


@pytest.mark.django_db
@pytest.mark.unit
class TestValidationServiceApproveAdminDeactivation:
    """Tests for ValidationService.approve_admin_deactivation method."""

    def test_approve_admin_deactivation_success(self):
        """Test successful admin deactivation."""
        organisme = OrganismeFactory()
        requester = AdminOrganismeFactory(id_organisme=organisme)
        target = AdminOrganismeFactory(id_organisme=organisme)
        validator = SuperAdminFactory()

        request = ValidationRequest.objects.create(
            request_type='admin_deactivation',
            status='pending',
            requester=requester,
            target_user=target
        )

        ValidationService.approve_admin_deactivation(request, validator)

        request.refresh_from_db()
        assert request.status == 'approved'

        target.refresh_from_db()
        assert target.active is False


@pytest.mark.django_db
@pytest.mark.unit
class TestValidationServiceApproveInviteOrgToSite:
    """Tests for ValidationService.approve_invite_org_to_site method."""

    def test_approve_invite_org_to_site_success(self):
        """Test successful org invitation approval."""
        site = SiteFactory()
        organisme = OrganismeFactory()
        requester = RoleFactory()
        validator = SuperAdminFactory()

        request = ValidationRequest.objects.create(
            request_type='invite_org_to_site',
            status='pending',
            requester=requester,
            target_site=site,
            requested_organisme=organisme
        )

        ValidationService.approve_invite_org_to_site(request, validator)

        request.refresh_from_db()
        assert request.status == 'approved'

        # Check link was created
        assert CorOgSite.objects.filter(id_site=site, uuid_og=organisme).exists()


@pytest.mark.django_db
@pytest.mark.unit
class TestValidationServiceApproveInviteUserToSite:
    """Tests for ValidationService.approve_invite_user_to_site method."""

    def test_approve_invite_user_to_site_success(self):
        """Test successful user invitation approval."""
        site = SiteFactory()
        target_user = RoleFactory()
        requester = RoleFactory()
        validator = SuperAdminFactory()

        request = ValidationRequest.objects.create(
            request_type='invite_user_to_site',
            status='pending',
            requester=requester,
            target_site=site,
            target_user=target_user
        )

        ValidationService.approve_invite_user_to_site(request, validator)

        request.refresh_from_db()
        assert request.status == 'approved'

        # Check user is linked to site
        assert CorRoleSite.objects.filter(id_role=target_user, id_site=site).exists()


@pytest.mark.django_db
@pytest.mark.unit
class TestValidationServiceApproveRegistration:
    """Tests for ValidationService.approve_registration method."""

    def test_approve_registration_success(self):
        """Test successful user registration approval."""
        from apps.notifications.models import PendingUser

        organisme = OrganismeFactory()
        validator = SuperAdminFactory()

        request = ValidationRequest.objects.create(
            request_type='user_registration',
            status='pending',
            requested_organisme=organisme
        )

        pending = PendingUser.objects.create(
            email='newuser@test.fr',
            nom_role='Dupont',
            prenom_role='Jean',
            requested_organisme=organisme,
            password_hash='pbkdf2_sha256$600000$test$hashvalue==',
            validation_request=request
        )

        user = ValidationService.approve_registration(request, validator, 'Welcome!')

        request.refresh_from_db()
        assert request.status == 'approved'
        assert user is not None
        assert user.email == 'newuser@test.fr'
        assert user.nom_role == 'Dupont'
        assert user.active is True

        # PendingUser should be deleted
        assert not PendingUser.objects.filter(email='newuser@test.fr').exists()

    def test_approve_registration_wrong_type(self):
        """Test error when trying to approve non-registration request."""
        request = ValidationRequestFactory(request_type='site_access', status='pending')
        validator = SuperAdminFactory()

        with pytest.raises(ValueError) as exc_info:
            ValidationService.approve_registration(request, validator)

        assert 'inscription' in str(exc_info.value).lower()


@pytest.mark.django_db
@pytest.mark.unit
class TestValidationServiceGetValidatorsForDifferentTypes:
    """Tests for ValidationService.get_validators_for_request with different request types."""

    def test_get_validators_admin_deactivation(self):
        """Test validators for admin deactivation are only super admins."""
        super_admin = SuperAdminFactory()
        target = AdminOrganismeFactory()

        request = ValidationRequest.objects.create(
            request_type='admin_deactivation',
            status='pending',
            target_user=target
        )

        validators = ValidationService.get_validators_for_request(request)
        validator_ids = [v.id_role for v in validators]

        assert super_admin.id_role in validator_ids

    def test_get_validators_registration(self):
        """Test validators for registration include org admins."""
        organisme = OrganismeFactory()
        admin_og = AdminOrganismeFactory(id_organisme=organisme)

        request = ValidationRequest.objects.create(
            request_type='user_registration',
            status='pending',
            requested_organisme=organisme
        )

        validators = ValidationService.get_validators_for_request(request)
        validator_ids = [v.id_role for v in validators]

        assert admin_og.id_role in validator_ids

    def test_get_validators_plan_access(self):
        """Test validators for plan access include plan referents."""
        site = SiteFactory()
        plan = PlanGestionFactory(statut='valide', sites=[site])

        referent = RoleFactory()
        CorRoleSiteFactory(id_role=referent, id_site=site, referent=True, referent_valid=True)
        plan.referents.add(referent)

        requester = RoleFactory()

        request = ValidationRequest.objects.create(
            request_type='plan_access',
            status='pending',
            requester=requester,
            target_plan=plan
        )

        validators = ValidationService.get_validators_for_request(request)
        validator_ids = [v.id_role for v in validators]

        assert referent.id_role in validator_ids
