"""
Integration tests for email sending.

These tests verify that emails are correctly sent via SMTP.
In development, Mailpit captures all emails (http://localhost:8025).
In production, emails are sent to real addresses.

They are marked with `email_integration` and are SKIPPED if using console backend.

Usage (development with Mailpit):
    # Mailpit is configured by default in docker compose
    docker compose up -d
    docker compose exec web pytest tests/apps/notifications/test_email_integration.py -m email_integration -v

    # View captured emails at http://localhost:8025

Usage (production SMTP):
    # Configure real SMTP in environment variables
    docker compose exec web pytest tests/apps/notifications/test_email_integration.py -m email_integration -v
"""
import os
import pytest
from datetime import timedelta
from django.conf import settings
from django.core import mail
from django.test.utils import override_settings
from django.utils import timezone

from apps.notifications.models import Notification, ValidationRequest, PendingUser
from apps.notifications.services import NotificationService, ValidationService
from apps.notifications.tasks import (
    send_notification_email,
    send_registration_pending_email,
    send_registration_approved_email,
    send_registration_rejected_email,
)
from apps.users.models import Role, Site, CorRoleSite, BibOrganismes
from tests.factories.users import (
    RoleFactory, SuperAdminFactory, AdminOrganismeFactory,
    SiteFactory, OrganismeFactory, CorRoleSiteFactory
)
from tests.factories.notifications import NotificationFactory, ValidationRequestFactory


# Default test email recipient
DEFAULT_TEST_EMAIL = 'test@reserves-naturelles.org'


def get_test_email():
    """Get the test email recipient from env or use default."""
    return os.environ.get('TEST_EMAIL_RECIPIENT', DEFAULT_TEST_EMAIL)


def is_email_backend_configured():
    """Check if email backend is configured for sending (SMTP, not console)."""
    # Accept any backend that actually sends emails (SMTP, Mailpit, etc.)
    # Reject console backend which just prints to stdout
    return 'console' not in settings.EMAIL_BACKEND.lower()


# Skip all tests in this module if using console backend
pytestmark = [
    pytest.mark.email_integration,
    pytest.mark.skipif(
        not is_email_backend_configured(),
        reason="Email backend is console. Use SMTP backend (Mailpit in dev, real SMTP in prod)"
    ),
]


@pytest.fixture(autouse=True)
def force_smtp_backend(settings):
    """
    Force SMTP backend for email integration tests.

    pytest-django can override email settings. This fixture ensures
    we use the real SMTP backend (Mailpit) for these tests.
    """
    settings.EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    settings.EMAIL_HOST = os.environ.get('EMAIL_HOST', 'mailpit')
    settings.EMAIL_PORT = int(os.environ.get('EMAIL_PORT', 1025))
    settings.EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', 'false').lower() == 'true'
    settings.EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
    settings.EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')


# =============================================================================
# NOTIFICATION EMAIL INTEGRATION TESTS
# =============================================================================

@pytest.mark.django_db
class TestNotificationEmailIntegration:
    """
    Integration tests for notification emails.

    These tests send REAL emails to test@reserves-naturelles.org.
    """

    def test_send_welcome_notification_email(self):
        """
        Test sending a welcome notification email.

        This creates a notification and sends it via the real SMTP backend.
        Check test@reserves-naturelles.org inbox for the email.
        """
        test_email = get_test_email()

        # Create user with real email
        user = RoleFactory(
            email=test_email,
            prenom_role='Test',
            nom_role='EmailRNF'
        )

        # Create welcome notification
        notification = NotificationFactory(
            recipient=user,
            notification_type='welcome',
            title='Bienvenue sur CICADA - Test Integration',
            message='Votre compte a ete active avec succes. Ceci est un email de test d\'integration.',
            priority='high',
            email_sent=False
        )

        # Send the email (synchronous call for testing)
        send_notification_email(notification.id)

        # Verify notification was marked as sent
        notification.refresh_from_db()
        assert notification.email_sent is True
        assert notification.email_sent_at is not None

        print(f"\n[SUCCESS] Welcome email sent to {test_email}")

    def test_send_validation_request_notification_email(self):
        """
        Test sending a validation request notification email to admin.

        Simulates notifying an admin of a new validation request.
        """
        test_email = get_test_email()

        # Create admin user with real email
        organisme = OrganismeFactory(nom_organisme='RNF Test')
        admin = AdminOrganismeFactory(
            email=test_email,
            prenom_role='Admin',
            nom_role='TestRNF',
            id_organisme=organisme
        )

        # Create validation request notification
        notification = NotificationFactory(
            recipient=admin,
            notification_type='validation_request',
            title='Nouvelle demande de validation - Test Integration',
            message='Un utilisateur a demande acces a un site. Veuillez traiter cette demande.',
            priority='high',
            email_sent=False
        )

        send_notification_email(notification.id)

        notification.refresh_from_db()
        assert notification.email_sent is True

        print(f"\n[SUCCESS] Validation request email sent to {test_email}")

    def test_send_account_deactivated_notification_email(self):
        """
        Test sending an account deactivation notification email.
        """
        test_email = get_test_email()

        user = RoleFactory(
            email=test_email,
            prenom_role='Test',
            nom_role='Deactivation'
        )

        notification = NotificationFactory(
            recipient=user,
            notification_type='account_deactivated',
            title='Compte desactive - Test Integration',
            message='Votre compte a ete desactive. Contactez un administrateur pour plus d\'informations.',
            priority='high',
            email_sent=False
        )

        send_notification_email(notification.id)

        notification.refresh_from_db()
        assert notification.email_sent is True

        print(f"\n[SUCCESS] Account deactivated email sent to {test_email}")

    def test_send_site_association_notification_email(self):
        """
        Test sending a site association notification email.
        """
        test_email = get_test_email()

        user = RoleFactory(
            email=test_email,
            prenom_role='Test',
            nom_role='SiteAssoc'
        )
        site = SiteFactory(nom_site='Reserve de Camargue - Test')

        notification = NotificationFactory(
            recipient=user,
            notification_type='user_associated_site',
            title='Acces au site accorde - Test Integration',
            message=f'Vous avez ete associe au site "{site.nom_site}".',
            priority='medium',
            related_site=site,
            email_sent=False
        )

        send_notification_email(notification.id)

        notification.refresh_from_db()
        assert notification.email_sent is True

        print(f"\n[SUCCESS] Site association email sent to {test_email}")


# =============================================================================
# REGISTRATION EMAIL INTEGRATION TESTS
# =============================================================================

@pytest.mark.django_db
class TestRegistrationEmailIntegration:
    """
    Integration tests for registration workflow emails.

    Tests the complete registration email flow:
    1. Registration pending (confirmation to new user)
    2. Registration approved (welcome to activated user)
    3. Registration rejected (denial notice)
    """

    def test_send_registration_pending_email_real(self):
        """
        Test sending registration pending confirmation email.

        This is sent when a user registers and awaits admin approval.
        """
        test_email = get_test_email()
        nom_complet = 'Test EmailPending RNF'

        send_registration_pending_email(test_email, nom_complet)

        print(f"\n[SUCCESS] Registration pending email sent to {test_email}")

    def test_send_registration_approved_email_real(self):
        """
        Test sending registration approved email.

        This is sent when an admin approves a user registration.
        """
        test_email = get_test_email()
        nom_complet = 'Test EmailApproved RNF'

        send_registration_approved_email(test_email, nom_complet)

        print(f"\n[SUCCESS] Registration approved email sent to {test_email}")

    def test_send_registration_rejected_email_real(self):
        """
        Test sending registration rejected email with reason.

        This is sent when an admin rejects a user registration.
        """
        test_email = get_test_email()
        reason = "Ceci est un test d'integration. L'organisme demande n'est pas partenaire de CICADA."

        send_registration_rejected_email(test_email, reason)

        print(f"\n[SUCCESS] Registration rejected email sent to {test_email}")

    def test_send_registration_rejected_email_no_reason(self):
        """
        Test sending registration rejected email without specific reason.
        """
        test_email = get_test_email()

        send_registration_rejected_email(test_email)

        print(f"\n[SUCCESS] Registration rejected (no reason) email sent to {test_email}")


# =============================================================================
# FULL WORKFLOW INTEGRATION TESTS
# =============================================================================

@pytest.mark.django_db
class TestFullWorkflowEmailIntegration:
    """
    Integration tests for complete email workflows.

    These tests simulate real-world scenarios and send multiple emails.
    """

    def test_complete_registration_workflow(self):
        """
        Test the complete user registration workflow with all emails.

        1. User registers -> pending email sent
        2. Admin approves -> approved email sent + welcome notification

        This test sends 3 emails total.
        """
        test_email = get_test_email()
        nom_complet = 'Test Workflow RNF'

        # Step 1: User registers (pending email)
        print(f"\n[STEP 1] Sending registration pending email to {test_email}...")
        send_registration_pending_email(test_email, nom_complet)
        print("[OK] Registration pending email sent")

        # Step 2: Admin approves (approved email)
        print(f"\n[STEP 2] Sending registration approved email to {test_email}...")
        send_registration_approved_email(test_email, nom_complet)
        print("[OK] Registration approved email sent")

        # Step 3: Welcome notification
        user = RoleFactory(
            email=test_email,
            prenom_role='Test',
            nom_role='Workflow'
        )
        notification = NotificationFactory(
            recipient=user,
            notification_type='welcome',
            title='Bienvenue sur CICADA',
            message='Votre compte est maintenant actif. Vous pouvez vous connecter.',
            priority='high',
            email_sent=False
        )

        print(f"\n[STEP 3] Sending welcome notification email to {test_email}...")
        send_notification_email(notification.id)
        print("[OK] Welcome notification email sent")

        notification.refresh_from_db()
        assert notification.email_sent is True

        print(f"\n[SUCCESS] Complete registration workflow: 3 emails sent to {test_email}")

    def test_site_access_workflow(self):
        """
        Test the site access request workflow with emails.

        1. User requests site access -> admin receives notification
        2. Admin approves -> user receives access granted notification

        This test sends 2 emails to the test address.
        """
        test_email = get_test_email()

        # Create site
        site = SiteFactory(nom_site='Reserve Test Integration')

        # Step 1: Admin notification (simulating user as admin for test)
        admin = RoleFactory(
            email=test_email,
            prenom_role='Admin',
            nom_role='SiteAccess',
            role_level='admin_og'
        )

        admin_notification = NotificationFactory(
            recipient=admin,
            notification_type='validation_request',
            title=f'Demande d\'acces - {site.nom_site}',
            message='Un utilisateur demande acces a ce site.',
            priority='high',
            related_site=site,
            email_sent=False
        )

        print(f"\n[STEP 1] Sending admin notification for site access request...")
        send_notification_email(admin_notification.id)
        print("[OK] Admin notification sent")

        # Step 2: User receives access granted (using same email for test)
        user_notification = NotificationFactory(
            recipient=admin,  # Same user for test
            notification_type='user_associated_site',
            title=f'Acces accorde - {site.nom_site}',
            message=f'Votre demande d\'acces au site "{site.nom_site}" a ete approuvee.',
            priority='medium',
            related_site=site,
            email_sent=False
        )

        print(f"\n[STEP 2] Sending access granted notification...")
        send_notification_email(user_notification.id)
        print("[OK] Access granted notification sent")

        admin_notification.refresh_from_db()
        user_notification.refresh_from_db()
        assert admin_notification.email_sent is True
        assert user_notification.email_sent is True

        print(f"\n[SUCCESS] Site access workflow: 2 emails sent to {test_email}")


# =============================================================================
# SERVICE LAYER INTEGRATION TESTS
# =============================================================================

@pytest.mark.django_db
class TestNotificationServiceEmailIntegration:
    """
    Integration tests for NotificationService with real emails.

    Tests that notifications created via the service layer
    correctly trigger email sending.
    """

    def test_create_notification_with_email(self):
        """
        Test creating a notification via NotificationService with email.
        """
        test_email = get_test_email()

        user = RoleFactory(
            email=test_email,
            prenom_role='Service',
            nom_role='Test'
        )

        # Create notification with send_email=True
        notification = NotificationService.create_notification(
            recipient=user,
            notification_type='info',
            title='Test via NotificationService',
            message='Cette notification a ete creee via NotificationService avec send_email=True.',
            priority='medium',
            send_email=True  # This should trigger email
        )

        # Note: With Celery, email is sent async. For sync testing, we call task directly.
        # In production with Celery, the task would be in the queue.

        # For this integration test, manually trigger email if not sent
        if not notification.email_sent:
            send_notification_email(notification.id)

        notification.refresh_from_db()
        assert notification.email_sent is True

        print(f"\n[SUCCESS] NotificationService email sent to {test_email}")

    def test_notify_super_admins(self):
        """
        Test notifying super admins via NotificationService.

        Note: This creates a super admin with the test email.
        """
        test_email = get_test_email()

        # Create super admin with test email
        super_admin = SuperAdminFactory(
            email=test_email,
            prenom_role='SuperAdmin',
            nom_role='EmailTest'
        )

        # Notify all super admins (method doesn't return notifications)
        NotificationService.notify_super_admins(
            notification_type='system_alert',
            title='Alerte Systeme - Test Integration',
            message='Ceci est une alerte systeme de test pour verifier l\'envoi aux super admins.',
            priority='high'
        )

        # Check our test super admin received the notification
        super_admin_notif = Notification.objects.filter(
            recipient=super_admin,
            notification_type='system_alert'
        ).first()

        assert super_admin_notif is not None, f"No notification created for {test_email}"

        # Send email if not already sent
        if not super_admin_notif.email_sent:
            send_notification_email(super_admin_notif.id)

        super_admin_notif.refresh_from_db()
        assert super_admin_notif.email_sent is True
        print(f"\n[SUCCESS] Super admin notification email sent to {test_email}")


# =============================================================================
# EMAIL TEMPLATE VERIFICATION TESTS
# =============================================================================

@pytest.mark.django_db
class TestEmailTemplatesIntegration:
    """
    Integration tests to verify all email templates render and send correctly.

    Each test sends a different type of email to verify templates.
    """

    @pytest.mark.parametrize("notification_type,title,message", [
        ('welcome', 'Bienvenue sur CICADA', 'Votre compte est actif.'),
        ('validation_request', 'Nouvelle demande', 'Une demande necessite votre attention.'),
        ('validation_approved', 'Demande approuvee', 'Votre demande a ete approuvee.'),
        ('validation_rejected', 'Demande refusee', 'Votre demande a ete refusee.'),
        ('user_associated_site', 'Acces site', 'Vous avez acces au site.'),
        ('user_associated_plan', 'Acces plan', 'Vous etes referent du plan.'),
        ('user_removed_site', 'Retrait site', 'Votre acces au site a ete retire.'),
        ('user_removed_plan', 'Retrait plan', 'Vous n\'etes plus referent du plan.'),
        ('account_deactivated', 'Compte desactive', 'Votre compte a ete desactive.'),
        ('account_activated', 'Compte active', 'Votre compte a ete reactive.'),
        ('organisme_changed', 'Changement organisme', 'Votre organisme a ete modifie.'),
        ('site_orphaned', 'Site orphelin', 'Un site n\'a plus d\'utilisateurs.'),
        ('organisme_no_admin', 'Organisme sans admin', 'Un organisme n\'a plus d\'administrateur.'),
        ('system_alert', 'Alerte systeme', 'Une alerte systeme a ete declenchee.'),
        ('info', 'Information', 'Ceci est une information generale.'),
    ])
    def test_notification_type_email(self, notification_type, title, message):
        """
        Test sending each notification type email.

        This parameterized test verifies all 15 notification types.
        """
        test_email = get_test_email()

        user = RoleFactory(
            email=test_email,
            prenom_role='Template',
            nom_role='Test'
        )

        notification = NotificationFactory(
            recipient=user,
            notification_type=notification_type,
            title=f'{title} - Test Integration',
            message=f'{message} (Type: {notification_type})',
            priority='medium',
            email_sent=False
        )

        send_notification_email(notification.id)

        notification.refresh_from_db()
        assert notification.email_sent is True

        print(f"\n[SUCCESS] {notification_type} email sent to {test_email}")
