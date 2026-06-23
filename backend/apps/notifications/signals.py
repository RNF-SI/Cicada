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
            title=f"Vous avez été associé au site {instance.id_site.nom_site}",
            message=f"Vous avez été ajouté comme membre du site {instance.id_site.nom_site}.",
            priority='medium',
            related_site=instance.id_site,
            action_url=f"/mes-sites/{instance.id_site.id_site}",
        )
        logger.info(f"User {instance.id_role} notified of site {instance.id_site} association")


# #446 — La détection « site orphelin » sur retrait d'utilisateur est gérée par
# `apps.users.signals.check_site_orphaned_after_user_removed` (post_delete
# CorRoleSite), qui dédoublonne via `_was_recently_notified` et filtre les
# utilisateurs actifs. Le handler équivalent qui vivait ici n'avait pas cette
# déduplication et, selon l'ordre d'exécution des signaux, produisait une
# notification en double. Il a donc été retiré pour éviter les doublons.


@receiver(post_delete, sender='users.CorRoleSite')
def notify_user_removed_from_site(sender, instance, **kwargs):
    """
    Notifie un utilisateur lorsqu'il est retire d'un site.
    Saute la notification si le site lui-même est en cours de suppression
    (CASCADE) : les utilisateurs sont déjà notifiés via
    `notify_users_before_site_delete` (pre_delete Site), et insérer une
    notification avec `related_site=site` ici violerait la FK au DELETE du site.
    """
    from apps.users.deletion_tracker import is_site_deleting
    from .services import NotificationService

    if is_site_deleting(instance.id_site_id):
        return

    try:
        NotificationService.create_notification(
            recipient=instance.id_role,
            notification_type='user_removed_site',
            title=f"Vous avez été retiré du site {instance.id_site.nom_site}",
            message=f"Vous n'êtes plus membre du site {instance.id_site.nom_site}.",
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
    Signal backup pour notifier les validateurs d'une nouvelle demande.

    NOTE: Ce signal ne fait RIEN car notify_validators() est appele
    explicitement dans les vues/serializers APRES creation des objets lies
    (PendingUser, etc.). Garder le signal causerait des notifications en double.
    """
    pass


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


@receiver(post_save, sender='plans.CorRolePlan')
def notify_plan_referents_new_member(sender, instance, created, **kwargs):
    """
    Notifie les referents d'un plan lorsqu'un nouvel utilisateur est ajoute comme membre.
    """
    if not created:
        return

    from .services import NotificationService
    from apps.users.models import Role

    plan = instance.plan_de_gestion
    new_user = instance.id_role
    user_name = f"{new_user.prenom_role} {new_user.nom_role}".strip() or new_user.email

    # Notifier chaque referent du plan (sauf le nouvel utilisateur lui-meme)
    for referent in plan.referents.filter(active=True).exclude(pk=new_user.pk):
        role_label = "référent" if instance.referent else "membre"
        NotificationService.create_notification(
            recipient=referent,
            notification_type='info',
            title=f"Nouvel utilisateur sur le plan {plan.nom}",
            message=f"{user_name} a été ajouté comme {role_label} du plan de gestion {plan.nom}.",
            priority='low',
            related_plan=plan,
            related_user=new_user,
            action_url=f"/plans/{plan.slug or plan.id_pg}",
        )
    logger.info(f"Plan {plan.nom} referents notified of new member {new_user}")


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
                        title=f"Vous êtes référent du plan {instance.nom}",
                        message=f"Vous avez été ajouté comme référent du plan de gestion {instance.nom}.",
                        priority='medium',
                        related_plan=instance,
                        action_url=f"/plans/{instance.id_pg}",
                    )
                except Role.DoesNotExist:
                    pass
