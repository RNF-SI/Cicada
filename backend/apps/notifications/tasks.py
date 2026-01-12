"""
Taches Celery pour les notifications et emails.
"""
import logging

from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def send_notification_email(self, notification_id):
    """
    Envoie un email pour une notification.

    Args:
        notification_id: ID de la notification
    """
    from .models import Notification
    from django.utils import timezone

    try:
        notification = Notification.objects.select_related('recipient').get(
            id=notification_id
        )
    except Notification.DoesNotExist:
        logger.error(f"Notification {notification_id} not found")
        return

    # Ne pas envoyer si deja envoye
    if notification.email_sent:
        return

    recipient_email = notification.recipient.email
    if not recipient_email:
        logger.warning(f"No email for recipient of notification {notification_id}")
        return

    try:
        # Construire le contenu de l'email
        context = {
            'notification': notification,
            'recipient': notification.recipient,
            'site_url': settings.SITE_URL if hasattr(settings, 'SITE_URL') else 'http://localhost:4200',
        }

        html_message = render_to_string(
            'emails/notification.html',
            context
        )
        plain_message = strip_tags(html_message)

        send_mail(
            subject=notification.title,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient_email],
            html_message=html_message,
            fail_silently=False,
        )

        # Marquer comme envoye
        notification.email_sent = True
        notification.email_sent_at = timezone.now()
        notification.save(update_fields=['email_sent', 'email_sent_at'])

        logger.info(f"Email sent for notification {notification_id}")

    except Exception as e:
        logger.error(f"Failed to send email for notification {notification_id}: {e}")
        # Retry avec backoff exponentiel
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))


@shared_task(bind=True, max_retries=3)
def send_registration_pending_email(self, email, nom_complet=None):
    """
    Envoie un email de confirmation d'inscription en attente.

    Args:
        email: Adresse email du demandeur
        nom_complet: Nom complet optionnel
    """
    try:
        context = {
            'nom_complet': nom_complet or email,
            'email': email,
            'site_url': settings.SITE_URL if hasattr(settings, 'SITE_URL') else 'http://localhost:4200',
        }

        html_message = render_to_string(
            'emails/registration_pending.html',
            context
        )
        plain_message = strip_tags(html_message)

        send_mail(
            subject="Demande d'inscription en attente de validation",
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            html_message=html_message,
            fail_silently=False,
        )

        logger.info(f"Registration pending email sent to {email}")

    except Exception as e:
        logger.error(f"Failed to send registration pending email to {email}: {e}")
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))


@shared_task(bind=True, max_retries=3)
def send_registration_approved_email(self, email, nom_complet=None):
    """
    Envoie un email de confirmation d'inscription approuvee.

    Args:
        email: Adresse email du nouvel utilisateur
        nom_complet: Nom complet optionnel
    """
    try:
        context = {
            'nom_complet': nom_complet or email,
            'email': email,
            'login_url': f"{settings.SITE_URL if hasattr(settings, 'SITE_URL') else 'http://localhost:4200'}/auth/login",
        }

        html_message = render_to_string(
            'emails/registration_approved.html',
            context
        )
        plain_message = strip_tags(html_message)

        send_mail(
            subject="Votre compte a ete valide",
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            html_message=html_message,
            fail_silently=False,
        )

        logger.info(f"Registration approved email sent to {email}")

    except Exception as e:
        logger.error(f"Failed to send registration approved email to {email}: {e}")
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))


@shared_task(bind=True, max_retries=3)
def send_registration_rejected_email(self, email, reason=None):
    """
    Envoie un email de notification de rejet d'inscription.

    Args:
        email: Adresse email du demandeur
        reason: Motif du rejet
    """
    try:
        context = {
            'email': email,
            'reason': reason or "Votre demande n'a pas ete validee.",
            'register_url': f"{settings.SITE_URL if hasattr(settings, 'SITE_URL') else 'http://localhost:4200'}/auth/register",
        }

        html_message = render_to_string(
            'emails/registration_rejected.html',
            context
        )
        plain_message = strip_tags(html_message)

        send_mail(
            subject="Demande d'inscription refusee",
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            html_message=html_message,
            fail_silently=False,
        )

        logger.info(f"Registration rejected email sent to {email}")

    except Exception as e:
        logger.error(f"Failed to send registration rejected email to {email}: {e}")
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))


@shared_task
def check_orphaned_sites():
    """
    Tache periodique pour verifier les sites sans utilisateurs.
    A executer quotidiennement.
    """
    from apps.users.models import Site, CorRoleSite
    from .services import NotificationService

    # Sites actifs sans aucun utilisateur associe
    sites_with_users = CorRoleSite.objects.values_list('id_site', flat=True)
    orphaned_sites = Site.objects.filter(
        active=True
    ).exclude(
        id_site__in=sites_with_users
    )

    for site in orphaned_sites:
        # Verifier si une notification n'a pas deja ete envoyee recemment
        from .models import Notification
        from django.utils import timezone
        from datetime import timedelta

        recent = Notification.objects.filter(
            notification_type='site_orphaned',
            related_site=site,
            created_at__gte=timezone.now() - timedelta(days=7)
        ).exists()

        if not recent:
            NotificationService.notify_site_orphaned(site)
            logger.info(f"Notification sent for orphaned site: {site.nom_site}")


@shared_task
def check_organismes_without_admin():
    """
    Tache periodique pour verifier les organismes sans admin_og.
    A executer quotidiennement.
    """
    from apps.users.models import BibOrganismes, Role
    from .services import NotificationService

    # Organismes sans admin_og actif
    organismes = BibOrganismes.objects.all()

    for organisme in organismes:
        has_admin = Role.objects.filter(
            id_organisme=organisme,
            role_level='admin_og',
            active=True
        ).exists()

        if not has_admin:
            # Verifier si une notification n'a pas deja ete envoyee recemment
            from .models import Notification
            from django.utils import timezone
            from datetime import timedelta

            recent = Notification.objects.filter(
                notification_type='organisme_no_admin',
                related_organisme=organisme,
                created_at__gte=timezone.now() - timedelta(days=7)
            ).exists()

            if not recent:
                NotificationService.notify_organisme_no_admin(organisme)
                logger.info(f"Notification sent for organisme without admin: {organisme.nom_organisme}")


@shared_task
def cleanup_old_notifications():
    """
    Tache periodique pour nettoyer les anciennes notifications.
    Supprime les notifications lues de plus de 90 jours.
    """
    from .models import Notification
    from django.utils import timezone
    from datetime import timedelta

    cutoff_date = timezone.now() - timedelta(days=90)

    deleted_count, _ = Notification.objects.filter(
        read=True,
        created_at__lt=cutoff_date
    ).delete()

    if deleted_count:
        logger.info(f"Cleaned up {deleted_count} old notifications")


@shared_task
def cleanup_expired_pending_users():
    """
    Tache periodique pour nettoyer les inscriptions en attente expirees.
    Supprime les PendingUser de plus de 30 jours.
    """
    from .models import PendingUser, ValidationRequest
    from django.utils import timezone
    from datetime import timedelta

    cutoff_date = timezone.now() - timedelta(days=30)

    # Marquer les demandes comme expirees
    expired_requests = ValidationRequest.objects.filter(
        request_type='user_registration',
        status='pending',
        created_at__lt=cutoff_date
    )

    count = expired_requests.count()
    expired_requests.update(status='expired')

    # Supprimer les PendingUser associes
    PendingUser.objects.filter(
        validation_request__status='expired'
    ).delete()

    if count:
        logger.info(f"Expired {count} pending registrations")
