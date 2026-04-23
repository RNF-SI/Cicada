"""
Signaux Django pour la gestion des utilisateurs.

Ce module gere les notifications en temps reel pour:
- Organismes sans admin_og (quand le dernier admin est desactive/supprime/retrograde)
- Sites orphelins (quand le dernier utilisateur est retire ou desactive)
- Suppressions d'organismes et de sites
- Desactivation de comptes utilisateurs
"""
import logging

from django.db.models.signals import pre_delete, post_save, post_delete
from django.dispatch import receiver
from django.utils import timezone
from datetime import timedelta

logger = logging.getLogger(__name__)


def _was_recently_notified(notification_type, related_site=None, related_organisme=None, days=7):
    """
    Verifie si une notification similaire a deja ete envoyee recemment.
    Evite le spam de notifications.
    """
    from apps.notifications.models import Notification

    filters = {
        'notification_type': notification_type,
        'created_at__gte': timezone.now() - timedelta(days=days)
    }

    if related_site:
        filters['related_site'] = related_site
    if related_organisme:
        filters['related_organisme'] = related_organisme

    return Notification.objects.filter(**filters).exists()


def _check_organisme_has_admin(organisme):
    """
    Verifie si un organisme a encore au moins un admin_og actif.
    Si non, envoie une notification aux super_admins.
    """
    from .models import Role
    from apps.notifications.services import NotificationService

    if not organisme:
        return

    has_admin = Role.objects.filter(
        id_organisme=organisme,
        role_level='admin_og',
        active=True
    ).exists()

    if not has_admin:
        # Verifier qu'on n'a pas deja notifie recemment
        if not _was_recently_notified('organisme_no_admin', related_organisme=organisme):
            NotificationService.notify_organisme_no_admin(organisme)
            logger.info(f"Signal: Notification sent for organisme without admin: {organisme.nom_organisme}")


def _check_site_has_users(site):
    """
    Verifie si un site a encore au moins un utilisateur actif.
    Si non, envoie une notification aux admins.
    """
    from .models import CorRoleSite
    from apps.notifications.services import NotificationService

    if not site or not site.active:
        return

    # Verifier s'il reste des utilisateurs actifs lies au site
    has_users = CorRoleSite.objects.filter(
        id_site=site,
        id_role__active=True
    ).exists()

    if not has_users:
        # Verifier qu'on n'a pas deja notifie recemment
        if not _was_recently_notified('site_orphaned', related_site=site):
            NotificationService.notify_site_orphaned(site)
            logger.info(f"Signal: Notification sent for orphaned site: {site.nom_site}")


@receiver(pre_delete, sender='users.BibOrganismes')
def notify_users_before_organisme_delete(sender, instance, **kwargs):
    """
    Notifie les utilisateurs avant la suppression d'un organisme.
    Ceci permet aux utilisateurs de savoir que leur organisme a ete supprime.
    """
    from .models import Role
    from apps.notifications.services import NotificationService

    organisme_name = instance.nom_organisme or f"Organisme #{instance.id_organisme}"

    # Trouver tous les utilisateurs lies a cet organisme
    affected_users = Role.objects.filter(
        id_organisme=instance,
        active=True
    )

    for user in affected_users:
        try:
            NotificationService.create_notification(
                recipient=user,
                notification_type='system_alert',
                title="Votre organisme a ete supprime",
                message=f"L'organisme '{organisme_name}' auquel vous etiez rattache "
                        f"a ete supprime du systeme. Veuillez contacter un administrateur "
                        f"pour etre rattache a un nouvel organisme.",
                priority='high',
                send_email=True
            )
            logger.info(f"Notified user {user.email} about organisme deletion: {organisme_name}")
        except Exception as e:
            logger.error(f"Error notifying user {user.email} about organisme deletion: {e}")

    # Notifier les super admins
    super_admins = Role.objects.filter(role_level='super_admin', active=True)
    for admin in super_admins:
        try:
            NotificationService.create_notification(
                recipient=admin,
                notification_type='system_alert',
                title="Organisme supprime",
                message=f"L'organisme '{organisme_name}' a ete supprime. "
                        f"{affected_users.count()} utilisateur(s) ont ete notifie(s).",
                priority='low'
            )
        except Exception as e:
            logger.error(f"Error notifying admin {admin.email} about organisme deletion: {e}")


@receiver(pre_delete, sender='users.Site')
def notify_users_before_site_delete(sender, instance, **kwargs):
    """
    Notifie les utilisateurs avant la suppression d'un site.
    Marque aussi le site pour que les signaux post_delete des enfants
    (CorRoleSite, etc.) sautent leur journalisation pendant la cascade.
    """
    from .models import Role, CorRoleSite
    from .deletion_tracker import mark_site_deleting
    from apps.notifications.services import NotificationService

    mark_site_deleting(instance.pk)

    site_name = instance.nom_site or f"Site #{instance.id_site}"

    # Trouver tous les utilisateurs lies a ce site
    affected_relations = CorRoleSite.objects.filter(id_site=instance).select_related('id_role')

    for relation in affected_relations:
        user = relation.id_role
        if not user.active:
            continue

        try:
            role_str = "referent" if relation.referent else "membre"
            NotificationService.create_notification(
                recipient=user,
                notification_type='system_alert',
                title="Un site auquel vous etiez associe a ete supprime",
                message=f"Le site '{site_name}' auquel vous etiez associe en tant que {role_str} "
                        f"a ete supprime du systeme.",
                priority='high',
                send_email=True
            )
            logger.info(f"Notified user {user.email} about site deletion: {site_name}")
        except Exception as e:
            logger.error(f"Error notifying user {user.email} about site deletion: {e}")


@receiver(post_delete, sender='users.Site')
def clear_site_deletion_marker(sender, instance, **kwargs):
    """Démarque le site une fois sa suppression effective."""
    from .deletion_tracker import unmark_site_deleting
    unmark_site_deleting(instance.pk)


@receiver(post_save, sender='users.Role')
def handle_user_deactivation(sender, instance, created, **kwargs):
    """
    Gere les actions apres la desactivation d'un utilisateur.
    Notifie l'utilisateur si son compte vient d'etre desactive.
    """
    if created:
        return

    # Verifier si l'utilisateur vient d'etre desactive
    # Note: Django ne fournit pas les anciennes valeurs directement,
    # donc on utilise le champ deactivated_at pour detecter une desactivation recente
    if not instance.active and instance.deactivated_at:
        from django.utils import timezone
        from datetime import timedelta

        # Si la desactivation est recente (moins de 1 minute), envoyer la notification
        if timezone.now() - instance.deactivated_at < timedelta(minutes=1):
            try:
                from apps.notifications.services import NotificationService

                NotificationService.create_notification(
                    recipient=instance,
                    notification_type='account_deactivated',
                    title="Votre compte a ete desactive",
                    message="Votre compte a ete desactive. Si vous pensez qu'il s'agit d'une erreur, "
                            "veuillez contacter un administrateur.",
                    priority='critical',
                    send_email=True
                )
                logger.info(f"Sent deactivation notification to {instance.email}")
            except Exception as e:
                logger.error(f"Error sending deactivation notification to {instance.email}: {e}")


# =============================================================================
# SIGNAUX POUR DETECTION EN TEMPS REEL DES PROBLEMES
# =============================================================================

@receiver(post_save, sender='users.Role')
def check_organisme_admin_after_role_change(sender, instance, created, **kwargs):
    """
    Verifie si un organisme a perdu son dernier admin_og apres une modification de Role.

    Cas detectes:
    - Un admin_og est retrograde en utilisateur (role_level change)
    - Un admin_og est desactive (active=False)
    - Un admin_og change d'organisme
    """
    if created:
        return

    # Si l'utilisateur etait potentiellement un admin_og
    # On verifie son organisme actuel
    if instance.id_organisme:
        _check_organisme_has_admin(instance.id_organisme)


@receiver(post_delete, sender='users.Role')
def check_organisme_admin_after_role_delete(sender, instance, **kwargs):
    """
    Verifie si un organisme a perdu son dernier admin_og apres suppression d'un Role.
    Verifie aussi si des sites sont devenus orphelins.
    """
    # Verifier l'organisme
    if instance.id_organisme:
        _check_organisme_has_admin(instance.id_organisme)

    # Verifier les sites lies a cet utilisateur
    # Note: Les CorRoleSite sont supprimes en cascade, mais le signal post_delete
    # sur CorRoleSite devrait s'en charger. Cependant, on peut aussi verifier ici.
    from .models import CorRoleSite
    for cor in CorRoleSite.objects.filter(id_role=instance):
        _check_site_has_users(cor.id_site)


@receiver(post_delete, sender='users.CorRoleSite')
def check_site_orphaned_after_user_removed(sender, instance, **kwargs):
    """
    Verifie si un site est devenu orphelin apres le retrait d'un utilisateur.
    Saute la vérification si le site lui-même est en cours de suppression
    (CASCADE) : il n'est pas orphelin, il est supprimé.
    """
    from .deletion_tracker import is_site_deleting

    if is_site_deleting(instance.id_site_id):
        return

    try:
        site = instance.id_site
        _check_site_has_users(site)
    except Exception as e:
        # Le site peut avoir ete supprime aussi
        logger.debug(f"Could not check site after CorRoleSite delete: {e}")


@receiver(post_save, sender='users.Role')
def check_sites_after_user_deactivation(sender, instance, created, **kwargs):
    """
    Verifie si des sites sont devenus orphelins apres la desactivation d'un utilisateur.

    Quand un utilisateur est desactive, tous les sites auxquels il etait lie
    peuvent potentiellement devenir orphelins.
    """
    if created:
        return

    # Si l'utilisateur vient d'etre desactive
    if not instance.active and instance.deactivated_at:
        # Si la desactivation est recente (moins de 1 minute)
        if timezone.now() - instance.deactivated_at < timedelta(minutes=1):
            from .models import CorRoleSite

            # Verifier tous les sites lies a cet utilisateur
            for cor in CorRoleSite.objects.filter(id_role=instance):
                _check_site_has_users(cor.id_site)
