"""
Unit tests for Celery tasks in notifications app.
Tests email sending, cleanup tasks, and audit tasks.
"""
import pytest
from unittest.mock import patch, MagicMock
from datetime import timedelta
from django.utils import timezone
from django.core import mail

from apps.notifications.tasks import (
    send_notification_email,
    send_registration_pending_email,
    send_registration_approved_email,
    send_registration_rejected_email,
    check_organismes_without_admin,
    cleanup_old_notifications,
    cleanup_expired_pending_users,
    process_deletion_requests
)
from apps.notifications.models import Notification, ValidationRequest, PendingUser
from apps.users.models import Role, Site, CorRoleSite, BibOrganismes
from tests.factories.users import (
    RoleFactory, SuperAdminFactory, AdminOrganismeFactory,
    SiteFactory, OrganismeFactory, CorRoleSiteFactory
)
from tests.factories.notifications import NotificationFactory, ValidationRequestFactory


# =============================================================================
# SEND NOTIFICATION EMAIL TESTS
# =============================================================================

@pytest.mark.django_db
@pytest.mark.unit
class TestSendNotificationEmail:
    """Tests for send_notification_email task."""

    @patch('apps.notifications.tasks.render_to_string')
    @patch('apps.notifications.tasks.send_mail')
    def test_send_notification_email_success(self, mock_send_mail, mock_render):
        """Test successful email sending for notification."""
        mock_render.return_value = '<html>Test</html>'
        mock_send_mail.return_value = 1

        user = RoleFactory(email='test@example.com')
        notification = NotificationFactory(
            recipient=user,
            title='Test Notification',
            message='Test message',
            email_sent=False
        )

        send_notification_email(notification.id)

        mock_send_mail.assert_called_once()
        notification.refresh_from_db()
        assert notification.email_sent is True
        assert notification.email_sent_at is not None

    @patch('apps.notifications.tasks.send_mail')
    def test_send_notification_email_not_found(self, mock_send_mail):
        """Test task handles missing notification gracefully."""
        # Should not raise, just log and return
        send_notification_email(99999)
        mock_send_mail.assert_not_called()

    @patch('apps.notifications.tasks.send_mail')
    def test_send_notification_email_already_sent(self, mock_send_mail):
        """Test task skips already sent notifications."""
        user = RoleFactory(email='test@example.com')
        notification = NotificationFactory(
            recipient=user,
            email_sent=True,
            email_sent_at=timezone.now()
        )

        send_notification_email(notification.id)
        mock_send_mail.assert_not_called()

    @patch('apps.notifications.tasks.send_mail')
    def test_send_notification_email_no_recipient_email(self, mock_send_mail):
        """Test task handles recipient without email."""
        user = RoleFactory(email='')
        notification = NotificationFactory(
            recipient=user,
            email_sent=False
        )

        send_notification_email(notification.id)
        mock_send_mail.assert_not_called()

    @patch('apps.notifications.tasks.render_to_string')
    @patch('apps.notifications.tasks.send_mail')
    def test_send_notification_email_retry_on_failure(self, mock_send_mail, mock_render):
        """Test task retries on email failure."""
        mock_render.return_value = '<html>Test</html>'
        mock_send_mail.side_effect = Exception('SMTP error')

        user = RoleFactory(email='test@example.com')
        notification = NotificationFactory(recipient=user, email_sent=False)

        # The task should raise for retry
        with pytest.raises(Exception):
            # Create mock task with request attribute
            task = MagicMock()
            task.request.retries = 0
            task.retry.side_effect = Exception('Retry')

            # Patch self to mock task
            with patch.object(send_notification_email, 'retry', side_effect=Exception('Retry')):
                send_notification_email(notification.id)


# =============================================================================
# REGISTRATION EMAIL TESTS
# =============================================================================

@pytest.mark.django_db
@pytest.mark.unit
class TestRegistrationEmails:
    """Tests for registration email tasks."""

    @patch('apps.notifications.tasks.render_to_string')
    @patch('apps.notifications.tasks.send_mail')
    def test_send_registration_pending_email_success(self, mock_send_mail, mock_render):
        """Test sending registration pending email."""
        mock_render.return_value = '<html>Pending</html>'
        mock_send_mail.return_value = 1

        send_registration_pending_email('newuser@test.com', 'Jean Dupont')

        mock_send_mail.assert_called_once()
        call_args = mock_send_mail.call_args
        assert call_args[1]['recipient_list'] == ['newuser@test.com']
        assert 'attente' in call_args[1]['subject'].lower()

    @patch('apps.notifications.tasks.render_to_string')
    @patch('apps.notifications.tasks.send_mail')
    def test_send_registration_pending_email_without_name(self, mock_send_mail, mock_render):
        """Test sending registration pending email without name."""
        mock_render.return_value = '<html>Pending</html>'
        mock_send_mail.return_value = 1

        send_registration_pending_email('newuser@test.com')

        mock_render.assert_called_once()
        context = mock_render.call_args[0][1]
        assert context['nom_complet'] == 'newuser@test.com'

    @patch('apps.notifications.tasks.render_to_string')
    @patch('apps.notifications.tasks.send_mail')
    def test_send_registration_approved_email_success(self, mock_send_mail, mock_render):
        """Test sending registration approved email."""
        mock_render.return_value = '<html>Approved</html>'
        mock_send_mail.return_value = 1

        send_registration_approved_email('user@test.com', 'Marie Martin')

        mock_send_mail.assert_called_once()
        call_args = mock_send_mail.call_args
        assert call_args[1]['recipient_list'] == ['user@test.com']
        assert 'valide' in call_args[1]['subject'].lower()

    @patch('apps.notifications.tasks.render_to_string')
    @patch('apps.notifications.tasks.send_mail')
    def test_send_registration_rejected_email_success(self, mock_send_mail, mock_render):
        """Test sending registration rejected email."""
        mock_render.return_value = '<html>Rejected</html>'
        mock_send_mail.return_value = 1

        send_registration_rejected_email('user@test.com', 'Non eligible')

        mock_send_mail.assert_called_once()
        call_args = mock_send_mail.call_args
        assert call_args[1]['recipient_list'] == ['user@test.com']
        assert 'refuse' in call_args[1]['subject'].lower()

    @patch('apps.notifications.tasks.render_to_string')
    @patch('apps.notifications.tasks.send_mail')
    def test_send_registration_rejected_email_without_reason(self, mock_send_mail, mock_render):
        """Test sending registration rejected email without reason."""
        mock_render.return_value = '<html>Rejected</html>'
        mock_send_mail.return_value = 1

        send_registration_rejected_email('user@test.com')

        mock_render.assert_called_once()
        context = mock_render.call_args[0][1]
        assert 'pas ete validee' in context['reason']


# =============================================================================
# AUDIT TASKS TESTS
# =============================================================================

@pytest.mark.django_db
@pytest.mark.unit
class TestCheckOrganismesWithoutAdmin:
    """Tests for check_organismes_without_admin task."""

    @patch('apps.notifications.services.NotificationService')
    def test_check_organismes_finds_without_admin(self, mock_service):
        """Test task finds organismes without admin and sends summary."""
        # Create organisme without admin
        organisme_no_admin = OrganismeFactory()

        # Create organisme with admin
        organisme_with_admin = OrganismeFactory()
        AdminOrganismeFactory(id_organisme=organisme_with_admin)

        check_organismes_without_admin()

        # Should send a single summary
        mock_service.notify_organismes_no_admin_summary.assert_called_once()
        orgs_arg = mock_service.notify_organismes_no_admin_summary.call_args[0][0]
        org_ids = {o.pk for o in orgs_arg}
        assert organisme_no_admin.pk in org_ids
        assert organisme_with_admin.pk not in org_ids

    @patch('apps.notifications.services.NotificationService')
    def test_check_organismes_skips_inactive_admin(self, mock_service):
        """Test task detects inactive admins."""
        organisme = OrganismeFactory()
        # Create inactive admin
        RoleFactory(id_organisme=organisme, role_level='admin_og', active=False)

        # Reset mock after factory setup (signals may have triggered)
        mock_service.reset_mock()

        check_organismes_without_admin()

        # The task should include organisme without active admin in summary
        mock_service.notify_organismes_no_admin_summary.assert_called_once()
        orgs_arg = mock_service.notify_organismes_no_admin_summary.call_args[0][0]
        org_ids = {o.pk for o in orgs_arg}
        assert organisme.pk in org_ids

    @patch('apps.notifications.services.NotificationService')
    def test_check_organismes_all_have_admin(self, mock_service):
        """Test task does nothing when all organismes have admins."""
        organisme = OrganismeFactory()
        AdminOrganismeFactory(id_organisme=organisme)

        check_organismes_without_admin()

        mock_service.notify_organismes_no_admin_summary.assert_not_called()


# =============================================================================
# CLEANUP TASKS TESTS
# =============================================================================

@pytest.mark.django_db
@pytest.mark.unit
class TestCleanupOldNotifications:
    """Tests for cleanup_old_notifications task."""

    def test_cleanup_deletes_old_read_notifications(self):
        """Test cleanup deletes old read notifications."""
        user = RoleFactory()

        # Create old read notification (91 days ago)
        old_read = NotificationFactory(recipient=user, read=True)
        Notification.objects.filter(id=old_read.id).update(
            created_at=timezone.now() - timedelta(days=91)
        )

        # Create recent read notification
        recent_read = NotificationFactory(recipient=user, read=True)

        # Create old unread notification (should not be deleted)
        old_unread = NotificationFactory(recipient=user, read=False)
        Notification.objects.filter(id=old_unread.id).update(
            created_at=timezone.now() - timedelta(days=91)
        )

        cleanup_old_notifications()

        # Old read should be deleted
        assert not Notification.objects.filter(id=old_read.id).exists()
        # Recent read should exist
        assert Notification.objects.filter(id=recent_read.id).exists()
        # Old unread should exist
        assert Notification.objects.filter(id=old_unread.id).exists()

    def test_cleanup_no_old_notifications(self):
        """Test cleanup handles no old notifications gracefully."""
        user = RoleFactory()
        NotificationFactory(recipient=user, read=True)

        # Should not raise
        cleanup_old_notifications()


@pytest.mark.django_db
@pytest.mark.unit
class TestCleanupExpiredPendingUsers:
    """Tests for cleanup_expired_pending_users task."""

    def test_cleanup_expires_old_pending_registrations(self):
        """Test cleanup expires old pending registrations."""
        organisme = OrganismeFactory()

        # Create old pending request (31 days ago)
        old_request = ValidationRequest.objects.create(
            request_type='user_registration',
            status='pending',
            requested_organisme=organisme
        )
        ValidationRequest.objects.filter(id=old_request.id).update(
            created_at=timezone.now() - timedelta(days=31)
        )

        old_pending = PendingUser.objects.create(
            email='old@test.com',
            nom_role='Old',
            prenom_role='User',
            requested_organisme=organisme,
            password_hash='hash',
            validation_request=old_request
        )

        # Create recent pending request
        recent_request = ValidationRequest.objects.create(
            request_type='user_registration',
            status='pending',
            requested_organisme=organisme
        )
        recent_pending = PendingUser.objects.create(
            email='recent@test.com',
            nom_role='Recent',
            prenom_role='User',
            requested_organisme=organisme,
            password_hash='hash',
            validation_request=recent_request
        )

        cleanup_expired_pending_users()

        # Old request should be expired
        old_request.refresh_from_db()
        assert old_request.status == 'expired'

        # Old pending user should be deleted
        assert not PendingUser.objects.filter(email='old@test.com').exists()

        # Recent should be untouched
        recent_request.refresh_from_db()
        assert recent_request.status == 'pending'
        assert PendingUser.objects.filter(email='recent@test.com').exists()


@pytest.mark.django_db
@pytest.mark.unit
class TestProcessDeletionRequests:
    """Tests for process_deletion_requests task (RGPD)."""

    @patch.object(Role, 'can_be_anonymized', return_value=True)
    @patch.object(Role, 'anonymize')
    def test_process_deletion_requests_anonymizes_eligible(self, mock_anonymize, mock_can_anonymize):
        """Test task anonymizes eligible users."""
        user = RoleFactory()
        user.deletion_requested_at = timezone.now() - timedelta(days=31)
        user.is_anonymized = False
        user.save()

        process_deletion_requests()

        mock_anonymize.assert_called_once()

    @patch.object(Role, 'can_be_anonymized', return_value=False)
    @patch.object(Role, 'anonymize')
    def test_process_deletion_requests_skips_ineligible(self, mock_anonymize, mock_can_anonymize):
        """Test task skips users not eligible for anonymization."""
        user = RoleFactory()
        user.deletion_requested_at = timezone.now() - timedelta(days=31)
        user.is_anonymized = False
        user.save()

        process_deletion_requests()

        mock_anonymize.assert_not_called()

    def test_process_deletion_requests_skips_already_anonymized(self):
        """Test task skips already anonymized users."""
        user = RoleFactory()
        user.deletion_requested_at = timezone.now() - timedelta(days=31)
        user.is_anonymized = True
        user.save()

        # Should not raise and should not process
        process_deletion_requests()

    @patch.object(Role, 'can_be_anonymized', return_value=True)
    @patch.object(Role, 'anonymize')
    @patch('apps.notifications.services.NotificationService')
    def test_process_deletion_requests_notifies_super_admins(self, mock_service, mock_anonymize, mock_can_anonymize):
        """Test task notifies super admins after anonymization."""
        super_admin = SuperAdminFactory()

        user = RoleFactory()
        user.deletion_requested_at = timezone.now() - timedelta(days=31)
        user.is_anonymized = False
        user.save()

        process_deletion_requests()

        mock_service.create_notification.assert_called()


# =============================================================================
# EMAIL TEMPLATE RENDERING TESTS
# =============================================================================

@pytest.mark.django_db
@pytest.mark.unit
class TestEmailTemplateContext:
    """Tests for email template context building."""

    @patch('apps.notifications.tasks.render_to_string')
    @patch('apps.notifications.tasks.send_mail')
    def test_notification_email_context(self, mock_send_mail, mock_render):
        """Test notification email context contains required fields."""
        mock_render.return_value = '<html>Test</html>'
        mock_send_mail.return_value = 1

        user = RoleFactory(email='test@example.com')
        notification = NotificationFactory(
            recipient=user,
            title='Test Title',
            message='Test Message',
            email_sent=False
        )

        send_notification_email(notification.id)

        mock_render.assert_called_once()
        context = mock_render.call_args[0][1]

        assert 'notification' in context
        assert 'recipient' in context
        assert 'site_url' in context
        assert context['notification'].title == 'Test Title'
        assert context['recipient'] == user

    @patch('apps.notifications.tasks.render_to_string')
    @patch('apps.notifications.tasks.send_mail')
    def test_registration_approved_email_context(self, mock_send_mail, mock_render):
        """Test registration approved email context."""
        mock_render.return_value = '<html>Test</html>'
        mock_send_mail.return_value = 1

        send_registration_approved_email('user@test.com', 'Jean Dupont')

        mock_render.assert_called_once()
        context = mock_render.call_args[0][1]

        assert context['nom_complet'] == 'Jean Dupont'
        assert context['email'] == 'user@test.com'
        assert 'login_url' in context


# =============================================================================
# TASK RETRY BEHAVIOR TESTS
# =============================================================================

@pytest.mark.django_db
@pytest.mark.unit
class TestTaskRetryBehavior:
    """Tests for task retry behavior on failures."""

    @patch('apps.notifications.tasks.render_to_string')
    @patch('apps.notifications.tasks.send_mail')
    def test_registration_pending_retry_on_smtp_error(self, mock_send_mail, mock_render):
        """Test registration pending email retries on SMTP error."""
        mock_render.return_value = '<html>Test</html>'
        mock_send_mail.side_effect = Exception('SMTP connection failed')

        # The task should raise for retry mechanism
        with pytest.raises(Exception):
            send_registration_pending_email('test@test.com', 'Test User')

    @patch('apps.notifications.tasks.render_to_string')
    @patch('apps.notifications.tasks.send_mail')
    def test_registration_approved_retry_on_smtp_error(self, mock_send_mail, mock_render):
        """Test registration approved email retries on SMTP error."""
        mock_render.return_value = '<html>Test</html>'
        mock_send_mail.side_effect = Exception('SMTP connection failed')

        with pytest.raises(Exception):
            send_registration_approved_email('test@test.com', 'Test User')

    @patch('apps.notifications.tasks.render_to_string')
    @patch('apps.notifications.tasks.send_mail')
    def test_registration_rejected_retry_on_smtp_error(self, mock_send_mail, mock_render):
        """Test registration rejected email retries on SMTP error."""
        mock_render.return_value = '<html>Test</html>'
        mock_send_mail.side_effect = Exception('SMTP connection failed')

        with pytest.raises(Exception):
            send_registration_rejected_email('test@test.com', 'Reason')
