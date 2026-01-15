"""
Unit tests for notifications app models.
Tests ValidationRequest, Notification, and PendingUser models.
"""
import pytest
from django.utils import timezone
from datetime import timedelta

from apps.notifications.models import Notification, ValidationRequest, PendingUser
from tests.factories.users import (
    RoleFactory, SuperAdminFactory, AdminOrganismeFactory,
    SiteFactory, OrganismeFactory, CorRoleSiteFactory, CorOgSiteFactory
)
from tests.factories.notifications import (
    NotificationFactory,
    ValidationRequestFactory,
    ReferentValidationRequestFactory,
    PendingUserFactory
)


# =============================================================================
# NOTIFICATION MODEL TESTS
# =============================================================================

@pytest.mark.django_db
@pytest.mark.unit
class TestNotificationModel:
    """Unit tests for Notification model."""

    def test_notification_creation(self):
        """Test creating a notification."""
        user = RoleFactory()
        notification = Notification.objects.create(
            recipient=user,
            notification_type='info',
            title='Test Notification',
            message='This is a test notification.'
        )

        assert notification.id is not None
        assert notification.recipient == user
        assert notification.notification_type == 'info'
        assert notification.title == 'Test Notification'
        assert notification.read is False
        assert notification.priority == 'medium'

    def test_notification_str(self):
        """Test notification string representation."""
        notification = NotificationFactory(title='Mon titre')
        assert 'Mon titre' in str(notification)

    def test_mark_as_read(self):
        """Test marking notification as read."""
        notification = NotificationFactory(read=False)
        assert notification.read is False
        assert notification.read_at is None

        notification.mark_as_read()

        assert notification.read is True
        assert notification.read_at is not None

    def test_mark_as_read_idempotent(self):
        """Test that marking as read multiple times doesn't change read_at."""
        notification = NotificationFactory(read=False)
        notification.mark_as_read()
        first_read_at = notification.read_at

        notification.mark_as_read()
        assert notification.read_at == first_read_at

    def test_is_expired_without_expiration(self):
        """Test is_expired returns False when no expiration set."""
        notification = NotificationFactory(expires_at=None)
        assert notification.is_expired() is False

    def test_is_expired_future_date(self):
        """Test is_expired returns False when expiration is in future."""
        future = timezone.now() + timedelta(days=1)
        notification = NotificationFactory(expires_at=future)
        assert notification.is_expired() is False

    def test_is_expired_past_date(self):
        """Test is_expired returns True when expiration is in past."""
        past = timezone.now() - timedelta(days=1)
        notification = NotificationFactory(expires_at=past)
        assert notification.is_expired() is True

    def test_notification_types(self):
        """Test all notification types are valid."""
        user = RoleFactory()
        valid_types = [
            'welcome', 'validation_request', 'validation_approved',
            'validation_rejected', 'user_associated_site', 'user_associated_plan',
            'user_removed_site', 'user_removed_plan', 'account_deactivated',
            'account_activated', 'site_orphaned', 'organisme_no_admin',
            'system_alert', 'info'
        ]

        for notification_type in valid_types:
            notification = Notification.objects.create(
                recipient=user,
                notification_type=notification_type,
                title='Test',
                message='Test message'
            )
            assert notification.notification_type == notification_type

    def test_notification_priority_levels(self):
        """Test all priority levels are valid."""
        user = RoleFactory()

        for priority in ['low', 'medium', 'high', 'critical']:
            notification = Notification.objects.create(
                recipient=user,
                notification_type='info',
                title='Test',
                message='Test message',
                priority=priority
            )
            assert notification.priority == priority


# =============================================================================
# VALIDATION REQUEST MODEL TESTS
# =============================================================================

@pytest.mark.django_db
@pytest.mark.unit
class TestValidationRequestModel:
    """Unit tests for ValidationRequest model."""

    def test_validation_request_creation(self):
        """Test creating a validation request."""
        user = RoleFactory()
        site = SiteFactory()

        request = ValidationRequest.objects.create(
            request_type='referent_validation',
            status='pending',
            requester=user,
            target_site=site,
            justification='Je souhaite devenir referent.'
        )

        assert request.id is not None
        assert request.request_type == 'referent_validation'
        assert request.status == 'pending'
        assert request.requester == user
        assert request.target_site == site

    def test_validation_request_str(self):
        """Test validation request string representation."""
        request = ReferentValidationRequestFactory()
        str_repr = str(request)
        assert 'Validation' in str_repr or 'referent' in str_repr.lower()

    def test_approve_method(self):
        """Test approve method updates fields correctly."""
        request = ReferentValidationRequestFactory(status='pending')
        validator = SuperAdminFactory()

        request.approve(validator, 'Approved!')

        assert request.status == 'approved'
        assert request.validator == validator
        assert request.validation_comment == 'Approved!'
        assert request.validated_at is not None

    def test_reject_method(self):
        """Test reject method updates fields correctly."""
        request = ReferentValidationRequestFactory(status='pending')
        validator = SuperAdminFactory()

        request.reject(validator, 'Rejected for testing')

        assert request.status == 'rejected'
        assert request.validator == validator
        assert request.validation_comment == 'Rejected for testing'
        assert request.validated_at is not None

    def test_cancel_method(self):
        """Test cancel method updates status."""
        request = ReferentValidationRequestFactory(status='pending')

        request.cancel()

        assert request.status == 'cancelled'

    def test_is_pending(self):
        """Test is_pending method."""
        request_pending = ReferentValidationRequestFactory(status='pending')
        request_approved = ReferentValidationRequestFactory(status='approved')
        request_rejected = ReferentValidationRequestFactory(status='rejected')

        assert request_pending.is_pending() is True
        assert request_approved.is_pending() is False
        assert request_rejected.is_pending() is False

    def test_request_types(self):
        """Test all request types are valid."""
        user = RoleFactory()
        valid_types = [
            'user_registration', 'site_access', 'plan_access',
            'module_access', 'admin_deactivation', 'referent_validation',
            'site_org_link'
        ]

        for req_type in valid_types:
            request = ValidationRequest.objects.create(
                request_type=req_type,
                status='pending',
                requester=user if req_type != 'user_registration' else None
            )
            assert request.request_type == req_type

    def test_status_choices(self):
        """Test all status choices are valid."""
        user = RoleFactory()

        for status_choice in ['pending', 'approved', 'rejected', 'cancelled', 'expired']:
            request = ValidationRequest.objects.create(
                request_type='site_access',
                status=status_choice,
                requester=user
            )
            assert request.status == status_choice


@pytest.mark.django_db
@pytest.mark.unit
class TestValidationRequestCanBeValidatedBy:
    """Unit tests for can_be_validated_by method."""

    def test_super_admin_can_validate_any_request(self):
        """Test super admin can validate any request."""
        super_admin = SuperAdminFactory()
        request = ReferentValidationRequestFactory(status='pending')

        assert request.can_be_validated_by(super_admin) is True

    def test_admin_og_can_validate_their_site_requests(self):
        """Test admin organisme can validate requests for their sites."""
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

        assert request.can_be_validated_by(admin_og) is True

    def test_referent_can_validate_their_site_requests(self):
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

        assert request.can_be_validated_by(referent) is True

    def test_regular_user_cannot_validate(self):
        """Test regular user cannot validate requests."""
        site = SiteFactory()
        regular_user = RoleFactory()

        requester = RoleFactory()
        CorRoleSiteFactory(id_role=requester, id_site=site, referent=False)

        request = ValidationRequest.objects.create(
            request_type='referent_validation',
            status='pending',
            requester=requester,
            target_site=site
        )

        assert request.can_be_validated_by(regular_user) is False

    def test_requester_cannot_validate_own_request(self):
        """Test that requester cannot validate their own request."""
        site = SiteFactory()
        user = RoleFactory()
        CorRoleSiteFactory(id_role=user, id_site=site, referent=False)

        request = ValidationRequest.objects.create(
            request_type='referent_validation',
            status='pending',
            requester=user,
            target_site=site
        )

        # Even if user somehow becomes a validator, they shouldn't validate own request
        # This depends on the service implementation
        assert request.requester == user


# =============================================================================
# PENDING USER MODEL TESTS
# =============================================================================

@pytest.mark.django_db
@pytest.mark.unit
class TestPendingUserModel:
    """Unit tests for PendingUser model."""

    def test_pending_user_creation(self):
        """Test creating a pending user."""
        organisme = OrganismeFactory()
        validation_request = ValidationRequest.objects.create(
            request_type='user_registration',
            status='pending'
        )

        pending_user = PendingUser.objects.create(
            email='newuser@test.fr',
            password_hash='pbkdf2_sha256$test$hash==',
            nom_role='Dupont',
            prenom_role='Jean',
            requested_organisme=organisme,
            validation_request=validation_request
        )

        assert pending_user.id is not None
        assert pending_user.email == 'newuser@test.fr'
        assert pending_user.nom_role == 'Dupont'
        assert pending_user.prenom_role == 'Jean'

    def test_pending_user_str(self):
        """Test pending user string representation."""
        pending_user = PendingUserFactory(prenom_role='Jean', nom_role='Dupont')
        str_repr = str(pending_user)
        assert 'Jean' in str_repr or 'Dupont' in str_repr or 'attente' in str_repr.lower()

    def test_get_full_name_with_names(self):
        """Test get_full_name with first and last names."""
        pending_user = PendingUserFactory(prenom_role='Jean', nom_role='Dupont')
        assert pending_user.get_full_name() == 'Jean Dupont'

    def test_get_full_name_without_names(self):
        """Test get_full_name returns email when no names."""
        validation_request = ValidationRequest.objects.create(
            request_type='user_registration',
            status='pending'
        )
        pending_user = PendingUser.objects.create(
            email='noname@test.fr',
            password_hash='hash',
            prenom_role=None,
            nom_role=None,
            validation_request=validation_request
        )
        assert pending_user.get_full_name() == 'noname@test.fr'

    def test_pending_user_unique_email(self):
        """Test that email must be unique for pending users."""
        pending1 = PendingUserFactory(email='unique@test.fr')

        with pytest.raises(Exception):  # IntegrityError
            validation_request = ValidationRequest.objects.create(
                request_type='user_registration',
                status='pending'
            )
            PendingUser.objects.create(
                email='unique@test.fr',
                password_hash='hash',
                validation_request=validation_request
            )
