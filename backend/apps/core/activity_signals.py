"""
Signaux Django pour l'enregistrement automatique de l'historique d'activite.

Ce module enregistre automatiquement les activites sur:
- Sites: creation, modification, suppression
- Plans de gestion: creation, modification, suppression, changement de statut
- Membres de site: ajout, retrait, changement de role referent
- Referents de plan: ajout, retrait
- Utilisateurs: creation, modification, desactivation, RGPD
- Organismes: creation, modification, suppression
- Validations: approbation, rejet

Les signaux sont automatiquement desactives pendant seed_testdata.
"""
import logging

from django.db.models.signals import post_save, post_delete, pre_save, pre_delete, m2m_changed
from django.dispatch import receiver

from .services import ActivityService

logger = logging.getLogger(__name__)


# =============================================================================
# UTILITAIRES POUR TRACKING DES CHANGEMENTS
# =============================================================================

def _get_tracked_changes(instance, tracked_fields):
    """
    Compare l'instance avec ses valeurs precedentes et retourne les changements.
    Utilise _previous_values stocke dans pre_save.
    """
    if not hasattr(instance, '_previous_values'):
        return {}

    changes = {}
    for field in tracked_fields:
        old_value = instance._previous_values.get(field)
        new_value = getattr(instance, field, None)

        # Convertir les FK en valeurs comparables
        if hasattr(old_value, 'pk'):
            old_value = old_value.pk
        if hasattr(new_value, 'pk'):
            new_value = new_value.pk

        if old_value != new_value:
            changes[field] = {
                'old': str(old_value) if old_value is not None else None,
                'new': str(new_value) if new_value is not None else None
            }

    return changes


def _store_previous_values(instance, tracked_fields):
    """
    Stocke les valeurs precedentes pour comparaison dans post_save.
    """
    instance._previous_values = {}
    for field in tracked_fields:
        instance._previous_values[field] = getattr(instance, field, None)


# =============================================================================
# SIGNAUX SITE
# =============================================================================

SITE_TRACKED_FIELDS = ['nom_site', 'active', 'surf_off', 'id_type_site']


@receiver(pre_save, sender='users.Site')
def track_site_previous_values(sender, instance, **kwargs):
    """
    Stocke les valeurs precedentes du site avant modification.
    """
    if instance.pk:
        try:
            from apps.users.models import Site
            old_instance = Site.objects.get(pk=instance.pk)
            _store_previous_values(old_instance, SITE_TRACKED_FIELDS)
            instance._previous_values = old_instance._previous_values
            instance._is_update = True
        except Site.DoesNotExist:
            instance._is_update = False
    else:
        instance._is_update = False


@receiver(post_save, sender='users.Site')
def log_site_activity_on_save(sender, instance, created, **kwargs):
    """
    Enregistre l'activite lors de la creation ou modification d'un site.
    """
    try:
        # Recuperer l'acteur depuis le contexte de la requete
        actor = getattr(instance, '_current_user', None)

        if created:
            ActivityService.log_site_activity(
                site=instance,
                action='create',
                actor=actor,
                description=f"Site \"{instance.nom_site}\" créé"
            )
        elif getattr(instance, '_is_update', False):
            changes = _get_tracked_changes(instance, SITE_TRACKED_FIELDS)
            if changes:
                ActivityService.log_site_activity(
                    site=instance,
                    action='update',
                    actor=actor,
                    description=f"Site \"{instance.nom_site}\" modifié",
                    changes=changes
                )
    except Exception as e:
        logger.error(f"Error logging site activity: {e}")


@receiver(pre_delete, sender='users.Site')
def log_site_activity_on_delete(sender, instance, **kwargs):
    """
    Enregistre l'activite lors de la suppression d'un site.
    """
    try:
        actor = getattr(instance, '_current_user', None)
        ActivityService.log_site_activity(
            site=instance,
            action='delete',
            actor=actor,
            description=f"Site \"{instance.nom_site}\" supprimé"
        )
    except Exception as e:
        logger.error(f"Error logging site deletion activity: {e}")


# =============================================================================
# SIGNAUX PLAN DE GESTION
# =============================================================================

PLAN_TRACKED_FIELDS = ['nom', 'statut', 'annee_debut', 'annee_fin', 'version', 'commentaire']


@receiver(pre_save, sender='plans.PlanGestion')
def track_plan_previous_values(sender, instance, **kwargs):
    """
    Stocke les valeurs precedentes du plan avant modification.
    """
    if instance.pk:
        try:
            from apps.plans.models import PlanGestion
            old_instance = PlanGestion.objects.get(pk=instance.pk)
            _store_previous_values(old_instance, PLAN_TRACKED_FIELDS)
            instance._previous_values = old_instance._previous_values
            instance._is_update = True
            instance._old_statut = old_instance.statut
        except PlanGestion.DoesNotExist:
            instance._is_update = False
    else:
        instance._is_update = False


@receiver(post_save, sender='plans.PlanGestion')
def log_plan_activity_on_save(sender, instance, created, **kwargs):
    """
    Enregistre l'activite lors de la creation ou modification d'un plan.
    """
    # Skip if explicitly flagged (e.g. during duplication)
    if getattr(instance, '_skip_activity_signal', False):
        return

    try:
        actor = getattr(instance, '_current_user', None)

        if created:
            ActivityService.log_plan_activity(
                plan=instance,
                action='create',
                actor=actor,
                description=f"Plan de gestion \"{instance.nom}\" créé"
            )
        elif getattr(instance, '_is_update', False):
            changes = _get_tracked_changes(instance, PLAN_TRACKED_FIELDS)

            # Verifier si c'est un changement de statut specifique
            old_statut = getattr(instance, '_old_statut', None)
            if old_statut and old_statut != instance.statut:
                ActivityService.log_plan_activity(
                    plan=instance,
                    action='status_change',
                    actor=actor,
                    description=f"Plan \"{instance.nom}\" : statut changé de \"{old_statut}\" à \"{instance.statut}\"",
                    changes={'statut': {'old': old_statut, 'new': instance.statut}}
                )
            elif changes:
                ActivityService.log_plan_activity(
                    plan=instance,
                    action='update',
                    actor=actor,
                    description=f"Plan de gestion \"{instance.nom}\" modifié",
                    changes=changes
                )
    except Exception as e:
        logger.error(f"Error logging plan activity: {e}")


@receiver(pre_delete, sender='plans.PlanGestion')
def log_plan_activity_on_delete(sender, instance, **kwargs):
    """
    Enregistre l'activite lors de la suppression d'un plan.
    """
    try:
        actor = getattr(instance, '_current_user', None)
        ActivityService.log_plan_activity(
            plan=instance,
            action='delete',
            actor=actor,
            description=f"Plan de gestion \"{instance.nom}\" supprimé"
        )
    except Exception as e:
        logger.error(f"Error logging plan deletion activity: {e}")


# =============================================================================
# SIGNAUX MEMBRES DE SITE (CorRoleSite)
# =============================================================================

@receiver(pre_save, sender='users.CorRoleSite')
def track_cor_role_site_previous_values(sender, instance, **kwargs):
    """
    Stocke les valeurs precedentes pour detecter les changements de referent.
    """
    if instance.pk:
        try:
            from apps.users.models import CorRoleSite
            old_instance = CorRoleSite.objects.get(pk=instance.pk)
            instance._previous_referent = old_instance.referent
            instance._previous_referent_valid = old_instance.referent_valid
            instance._is_update = True
        except CorRoleSite.DoesNotExist:
            instance._is_update = False
    else:
        instance._is_update = False


@receiver(post_save, sender='users.CorRoleSite')
def log_member_activity_on_save(sender, instance, created, **kwargs):
    """
    Enregistre l'activite lors de l'ajout ou modification d'un membre de site.
    """
    try:
        actor = getattr(instance, '_current_user', None)

        if created:
            if instance.referent and instance.referent_valid:
                action = 'add_referent'
            else:
                action = 'add_member'

            ActivityService.log_member_change(
                site=instance.id_site,
                user=instance.id_role,
                action=action,
                actor=actor,
                is_referent=instance.referent and instance.referent_valid
            )
        elif getattr(instance, '_is_update', False):
            # Detecter si le statut referent a change
            prev_was_referent = (
                getattr(instance, '_previous_referent', False) and
                getattr(instance, '_previous_referent_valid', False)
            )
            now_is_referent = instance.referent and instance.referent_valid

            if not prev_was_referent and now_is_referent:
                ActivityService.log_member_change(
                    site=instance.id_site,
                    user=instance.id_role,
                    action='add_referent',
                    actor=actor,
                    is_referent=True
                )
            elif prev_was_referent and not now_is_referent:
                ActivityService.log_member_change(
                    site=instance.id_site,
                    user=instance.id_role,
                    action='remove_referent',
                    actor=actor,
                    is_referent=False
                )
    except Exception as e:
        logger.error(f"Error logging member activity: {e}")


@receiver(post_delete, sender='users.CorRoleSite')
def log_member_activity_on_delete(sender, instance, **kwargs):
    """
    Enregistre l'activite lors du retrait d'un membre de site.
    Saute la journalisation si le site lui-même est en cours de suppression
    (CASCADE) : la suppression du site est déjà loggée, et écrire une ligne
    avec `related_site=site` ici violerait la FK au moment du DELETE du site.
    """
    from apps.users.deletion_tracker import is_site_deleting

    if is_site_deleting(instance.id_site_id):
        return

    try:
        actor = getattr(instance, '_current_user', None)
        was_referent = instance.referent and instance.referent_valid

        ActivityService.log_member_change(
            site=instance.id_site,
            user=instance.id_role,
            action='remove_member',
            actor=actor,
            is_referent=was_referent
        )
    except Exception as e:
        logger.error(f"Error logging member removal activity: {e}")


# =============================================================================
# SIGNAUX REFERENTS DE PLAN (M2M)
# =============================================================================

@receiver(m2m_changed, sender='plans.PlanGestion_referents')
def log_plan_referent_activity(sender, instance, action, pk_set, **kwargs):
    """
    Enregistre l'activite lors de l'ajout ou retrait de referents de plan.
    """
    if action not in ('post_add', 'post_remove'):
        return

    try:
        from apps.users.models import Role

        actor = getattr(instance, '_current_user', None)
        log_action = 'add_referent' if action == 'post_add' else 'remove_referent'

        for user_id in pk_set:
            try:
                user = Role.objects.get(pk=user_id)
                ActivityService.log_plan_referent_change(
                    plan=instance,
                    user=user,
                    action=log_action,
                    actor=actor
                )
            except Role.DoesNotExist:
                logger.warning(f"User {user_id} not found for plan referent activity")
    except Exception as e:
        logger.error(f"Error logging plan referent activity: {e}")


# =============================================================================
# SIGNAUX UTILISATEUR
# =============================================================================

USER_TRACKED_FIELDS = ['nom_role', 'prenom_role', 'email', 'role_level', 'active', 'id_organisme']


@receiver(pre_save, sender='users.Role')
def track_user_previous_values(sender, instance, **kwargs):
    """
    Stocke les valeurs precedentes de l'utilisateur avant modification.
    """
    if instance.pk:
        try:
            from apps.users.models import Role
            old_instance = Role.objects.get(pk=instance.pk)
            _store_previous_values(old_instance, USER_TRACKED_FIELDS)
            instance._previous_values = old_instance._previous_values
            instance._is_update = True
            instance._was_active = old_instance.active
            instance._old_deletion_requested = old_instance.deletion_requested_at
        except Role.DoesNotExist:
            instance._is_update = False
    else:
        instance._is_update = False


@receiver(post_save, sender='users.Role')
def log_user_activity_on_save(sender, instance, created, **kwargs):
    """
    Enregistre l'activite lors de la creation ou modification d'un utilisateur.
    """
    try:
        actor = getattr(instance, '_current_user', None)

        if created and not instance.pending_validation:
            ActivityService.log_user_activity(
                user=instance,
                action='create',
                actor=actor,
                description=f"Utilisateur \"{instance.get_full_name()}\" créé",
                visibility='admin'
            )
        elif getattr(instance, '_is_update', False):
            # Detecter la desactivation
            was_active = getattr(instance, '_was_active', True)
            if was_active and not instance.active:
                ActivityService.log_user_activity(
                    user=instance,
                    action='deactivate',
                    actor=actor,
                    description=f"Compte de \"{instance.get_full_name()}\" désactivé",
                    metadata={'reason': instance.deactivation_reason} if instance.deactivation_reason else {},
                    visibility='admin'
                )
            elif not was_active and instance.active:
                ActivityService.log_user_activity(
                    user=instance,
                    action='activate',
                    actor=actor,
                    description=f"Compte de \"{instance.get_full_name()}\" réactivé",
                    visibility='admin'
                )

            # Detecter la demande de suppression RGPD
            old_deletion = getattr(instance, '_old_deletion_requested', None)
            if not old_deletion and instance.deletion_requested_at:
                ActivityService.log_rgpd_activity(
                    user=instance,
                    action='rgpd_request',
                    actor=actor or instance,
                    description=f"Demande de suppression RGPD pour \"{instance.get_full_name()}\""
                )
            elif old_deletion and not instance.deletion_requested_at:
                ActivityService.log_rgpd_activity(
                    user=instance,
                    action='rgpd_cancelled',
                    actor=actor,
                    description=f"Demande de suppression RGPD annulée pour \"{instance.get_full_name()}\""
                )

            # Detecter l'anonymisation
            if instance.is_anonymized and not getattr(instance, '_was_anonymized', False):
                ActivityService.log_rgpd_activity(
                    user=instance,
                    action='rgpd_anonymized',
                    actor=actor,
                    description=f"Compte anonymisé suite à demande RGPD"
                )

            # Autres changements
            changes = _get_tracked_changes(instance, USER_TRACKED_FIELDS)
            # Filtrer les changements deja traites
            changes.pop('active', None)
            if changes:
                ActivityService.log_user_activity(
                    user=instance,
                    action='update',
                    actor=actor,
                    description=f"Utilisateur \"{instance.get_full_name()}\" modifié",
                    changes=changes,
                    visibility='admin'
                )
    except Exception as e:
        logger.error(f"Error logging user activity: {e}")


# =============================================================================
# SIGNAUX ORGANISME
# =============================================================================

ORGANISME_TRACKED_FIELDS = ['nom_organisme', 'email_organisme', 'ville_organisme']


@receiver(pre_save, sender='users.BibOrganismes')
def track_organisme_previous_values(sender, instance, **kwargs):
    """
    Stocke les valeurs precedentes de l'organisme avant modification.
    """
    if instance.pk:
        try:
            from apps.users.models import BibOrganismes
            old_instance = BibOrganismes.objects.get(pk=instance.pk)
            _store_previous_values(old_instance, ORGANISME_TRACKED_FIELDS)
            instance._previous_values = old_instance._previous_values
            instance._is_update = True
        except BibOrganismes.DoesNotExist:
            instance._is_update = False
    else:
        instance._is_update = False


@receiver(post_save, sender='users.BibOrganismes')
def log_organisme_activity_on_save(sender, instance, created, **kwargs):
    """
    Enregistre l'activite lors de la creation ou modification d'un organisme.
    """
    try:
        actor = getattr(instance, '_current_user', None)

        if created:
            ActivityService.log_organisme_activity(
                organisme=instance,
                action='create',
                actor=actor,
                description=f"Organisme \"{instance.nom_organisme}\" créé",
                visibility='admin'
            )
        elif getattr(instance, '_is_update', False):
            changes = _get_tracked_changes(instance, ORGANISME_TRACKED_FIELDS)
            if changes:
                ActivityService.log_organisme_activity(
                    organisme=instance,
                    action='update',
                    actor=actor,
                    description=f"Organisme \"{instance.nom_organisme}\" modifié",
                    changes=changes,
                    visibility='admin'
                )
    except Exception as e:
        logger.error(f"Error logging organisme activity: {e}")


@receiver(pre_delete, sender='users.BibOrganismes')
def log_organisme_activity_on_delete(sender, instance, **kwargs):
    """
    Enregistre l'activite lors de la suppression d'un organisme.
    """
    try:
        actor = getattr(instance, '_current_user', None)
        ActivityService.log_organisme_activity(
            organisme=instance,
            action='delete',
            actor=actor,
            description=f"Organisme \"{instance.nom_organisme}\" supprimé",
            visibility='admin'
        )
    except Exception as e:
        logger.error(f"Error logging organisme deletion activity: {e}")


# =============================================================================
# SIGNAUX VALIDATION
# =============================================================================

@receiver(pre_save, sender='notifications.ValidationRequest')
def track_validation_previous_status(sender, instance, **kwargs):
    """
    Stocke le statut precedent de la demande de validation.
    """
    if instance.pk:
        try:
            from apps.notifications.models import ValidationRequest
            old_instance = ValidationRequest.objects.get(pk=instance.pk)
            instance._previous_status = old_instance.status
            instance._is_update = True
        except ValidationRequest.DoesNotExist:
            instance._is_update = False
    else:
        instance._is_update = False


@receiver(post_save, sender='notifications.ValidationRequest')
def log_validation_activity_on_save(sender, instance, created, **kwargs):
    """
    Enregistre l'activite lors d'un changement de statut de validation.
    """
    try:
        if not getattr(instance, '_is_update', False):
            return

        old_status = getattr(instance, '_previous_status', None)
        if old_status == instance.status:
            return

        # Seuls les changements vers approved/rejected sont loggues
        if instance.status == 'approved':
            ActivityService.log_validation_activity(
                validation=instance,
                action='validation_approved',
                actor=instance.validator,
                description=f"{instance.get_request_type_display()} approuvée"
            )
        elif instance.status == 'rejected':
            ActivityService.log_validation_activity(
                validation=instance,
                action='validation_rejected',
                actor=instance.validator,
                description=f"{instance.get_request_type_display()} rejetée",
                metadata={'comment': instance.validation_comment} if instance.validation_comment else {}
            )
    except Exception as e:
        logger.error(f"Error logging validation activity: {e}")
