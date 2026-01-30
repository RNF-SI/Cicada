"""
Signals Django pour les notifications automatiques.
"""
import logging

from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver

logger = logging.getLogger(__name__)


@receiver(post_save, sender='users.CorRoleSite')
def notify_user_site_association(sender, instance, created, **kwargs):
    """
    Notifie un utilisateur lorsqu'il est associe a un site.
    Evite les doublons si une notification similaire existe deja (ex: via validation).
    """
    if created:
        from .services import NotificationService
        from .models import Notification
        from django.utils import timezone
        from datetime import timedelta

        # Verifier si une notification similaire existe deja (creee dans les 30 derniers secondes)
        # Cela evite les doublons quand l'association vient d'une validation approuvee
        recent_threshold = timezone.now() - timedelta(seconds=30)
        existing = Notification.objects.filter(
            recipient=instance.id_role,
            related_site=instance.id_site,
            notification_type='user_associated_site',
            created_at__gte=recent_threshold
        ).exists()

        if existing:
            logger.debug(f"Skipping duplicate notification for user {instance.id_role} site {instance.id_site}")
            return

        NotificationService.create_notification(
            recipient=instance.id_role,
            notification_type='user_associated_site',
            title=f"Vous avez ete associe au site {instance.id_site.nom_site}",
            message=f"Vous avez ete ajoute comme membre du site {instance.id_site.nom_site}.",
            priority='medium',
            related_site=instance.id_site,
            action_url=f"/mes-sites/{instance.id_site.id_site}",
        )
        logger.info(f"User {instance.id_role} notified of site {instance.id_site} association")


@receiver(post_delete, sender='users.CorRoleSite')
def check_site_orphaned_on_user_removal(sender, instance, **kwargs):
    """
    Verifie si un site devient orphelin apres le retrait d'un utilisateur.
    """
    from apps.users.models import CorRoleSite
    from .services import NotificationService

    site = instance.id_site

    # Verifier s'il reste des utilisateurs sur ce site
    remaining_users = CorRoleSite.objects.filter(id_site=site).exists()

    if not remaining_users:
        NotificationService.notify_site_orphaned(site)
        logger.info(f"Site {site.nom_site} is now orphaned")


@receiver(post_delete, sender='users.CorRoleSite')
def notify_user_removed_from_site(sender, instance, **kwargs):
    """
    Notifie un utilisateur lorsqu'il est retire d'un site.
    """
    from .services import NotificationService

    try:
        NotificationService.create_notification(
            recipient=instance.id_role,
            notification_type='user_removed_site',
            title=f"Vous avez ete retire du site {instance.id_site.nom_site}",
            message=f"Vous n'etes plus membre du site {instance.id_site.nom_site}.",
            priority='medium',
            related_site=instance.id_site,
        )
    except Exception as e:
        # L'utilisateur peut avoir ete supprime aussi
        logger.warning(f"Could not notify user removal from site: {e}")


@receiver(pre_save, sender='users.Role')
def track_user_deactivation(sender, instance, **kwargs):
    """
    Detecte la desactivation d'un utilisateur.
    """
    if not instance.pk:
        return

    try:
        from apps.users.models import Role
        old_instance = Role.objects.get(pk=instance.pk)

        # Detecter la desactivation
        if old_instance.active and not instance.active:
            # Stocker l'info pour post_save
            instance._was_deactivated = True
            instance._was_active = old_instance.active
        else:
            instance._was_deactivated = False

        # Detecter le changement d'organisme
        instance._old_organisme = old_instance.id_organisme
    except sender.DoesNotExist:
        instance._was_deactivated = False
        instance._old_organisme = None


@receiver(post_save, sender='users.Role')
def notify_user_deactivation(sender, instance, created, **kwargs):
    """
    Notifie les super admins de la desactivation d'un utilisateur.
    """
    if created:
        return

    if getattr(instance, '_was_deactivated', False):
        from .services import NotificationService

        # Ne pas notifier si c'est une auto-desactivation
        if instance.deactivated_by and instance.deactivated_by != instance:
            NotificationService.notify_user_deactivated(
                user=instance,
                deactivated_by=instance.deactivated_by,
                reason=instance.deactivation_reason
            )
            logger.info(f"User {instance} was deactivated by {instance.deactivated_by}")


@receiver(post_save, sender='users.Role')
def notify_user_organisme_changed(sender, instance, created, **kwargs):
    """
    Notifie un utilisateur lorsque son organisme est modifie par un admin.
    """
    if created:
        return

    old_organisme = getattr(instance, '_old_organisme', None)
    new_organisme = instance.id_organisme

    # Verifier si l'organisme a change
    if old_organisme is None and new_organisme is None:
        return
    if old_organisme and new_organisme and old_organisme.pk == new_organisme.pk:
        return

    from .services import NotificationService

    old_name = old_organisme.nom_organisme if old_organisme else "Aucun"
    new_name = new_organisme.nom_organisme if new_organisme else "Aucun"

    NotificationService.create_notification(
        recipient=instance,
        notification_type='organisme_changed',
        title="Votre organisme a été modifié",
        message=f"Votre organisme a été changé de \"{old_name}\" vers \"{new_name}\".",
        priority='high',
        related_organisme=new_organisme,
        action_url="/profile",
    )
    logger.info(f"User {instance} notified of organisme change: {old_name} -> {new_name}")


@receiver(post_save, sender='notifications.ValidationRequest')
def notify_new_validation_request(sender, instance, created, **kwargs):
    """
    Notifie les validateurs d'une nouvelle demande.
    """
    if created and instance.status == 'pending':
        from .services import NotificationService
        NotificationService.notify_validators(instance)
        logger.info(f"Validators notified of new {instance.request_type} request")


@receiver(post_save, sender='notifications.ValidationRequest')
def handle_validation_result(sender, instance, created, **kwargs):
    """
    Gere le resultat d'une validation (hors du flux normal).
    Ce signal est un backup si la validation n'est pas faite via le service.
    """
    if created:
        return

    # Verifier si le statut vient de changer
    if not hasattr(instance, '_original_status'):
        return

    if instance._original_status == 'pending' and instance.status in ['approved', 'rejected']:
        from .services import NotificationService

        # Le service devrait deja avoir envoye la notification,
        # mais on verifie au cas ou
        from .models import Notification

        existing = Notification.objects.filter(
            related_validation=instance,
            notification_type__in=['validation_approved', 'validation_rejected']
        ).exists()

        if not existing and instance.requester:
            NotificationService.notify_validation_result(
                instance,
                approved=(instance.status == 'approved')
            )


@receiver(pre_save, sender='notifications.ValidationRequest')
def track_validation_status(sender, instance, **kwargs):
    """
    Stocke le statut original pour detecter les changements.
    """
    if instance.pk:
        try:
            from .models import ValidationRequest
            old = ValidationRequest.objects.get(pk=instance.pk)
            instance._original_status = old.status
        except ValidationRequest.DoesNotExist:
            instance._original_status = None
    else:
        instance._original_status = None


@receiver(post_save, sender='plans.PlanGestion')
def notify_plan_referent_association(sender, instance, created, **kwargs):
    """
    Notifie les referents ajoutes a un plan de gestion.
    Note: Cette notification est geree via M2M changed signal.
    """
    pass  # Gere par le signal m2m_changed ci-dessous


def setup_m2m_signals():
    """
    Configure les signals pour les relations M2M.
    A appeler dans apps.py ready().
    """
    from django.db.models.signals import m2m_changed
    from apps.plans.models import PlanGestion

    @receiver(m2m_changed, sender=PlanGestion.referents.through)
    def notify_plan_referent_change(sender, instance, action, pk_set, **kwargs):
        """
        Notifie les utilisateurs ajoutes comme referents d'un plan.
        """
        if action == 'post_add' and pk_set:
            from apps.users.models import Role
            from .services import NotificationService

            for role_id in pk_set:
                try:
                    role = Role.objects.get(pk=role_id)
                    NotificationService.create_notification(
                        recipient=role,
                        notification_type='user_associated_plan',
                        title=f"Vous etes referent du plan {instance.nom}",
                        message=f"Vous avez ete ajoute comme referent du plan de gestion {instance.nom}.",
                        priority='medium',
                        related_plan=instance,
                        action_url=f"/plans/{instance.id_pg}",
                    )
                except Role.DoesNotExist:
                    pass
