"""
Services pour le module core.
Contient le service ActivityService pour la gestion de l'historique d'activite.
"""
import logging
from typing import Optional, Any

from django.db.models import Model
from django.utils.translation import gettext_lazy as _

from .models import ActivityLog

logger = logging.getLogger(__name__)


class ActivityService:
    """
    Service pour l'enregistrement et la gestion de l'historique d'activite.

    Usage:
        ActivityService.log_site_activity(site, 'create', user, "Site créé")
        ActivityService.log_plan_activity(plan, 'update', user, "Plan modifié", changes={'nom': {'old': 'A', 'new': 'B'}})
        ActivityService.log_rgpd_activity(target_user, 'rgpd_request', actor, "Demande de suppression")
    """

    @staticmethod
    def log_activity(
        entity_type: str,
        entity_id: int,
        entity_name: str,
        action: str,
        actor: Optional['users.Role'],
        description: str,
        related_site: Optional[Model] = None,
        related_plan: Optional[Model] = None,
        related_organisme: Optional[Model] = None,
        related_user: Optional[Model] = None,
        changes: Optional[dict] = None,
        metadata: Optional[dict] = None,
        visibility: str = 'public'
    ) -> ActivityLog:
        """
        Enregistre une activite sur une entite.

        Args:
            entity_type: Type de l'entite (site, plan, user, organisme, validation)
            entity_id: ID de l'entite
            entity_name: Nom de l'entite (denormalise)
            action: Type d'action (create, update, delete, etc.)
            actor: Utilisateur qui effectue l'action (peut etre None pour actions systeme)
            description: Description lisible de l'action
            related_site: Site lie a l'activite (optionnel)
            related_plan: Plan lie a l'activite (optionnel)
            related_organisme: Organisme lie a l'activite (optionnel)
            related_user: Utilisateur concerne par l'activite (optionnel)
            changes: Dict des changements {field: {old, new}}
            metadata: Metadonnees additionnelles
            visibility: Niveau de visibilite (public, admin, system)

        Returns:
            ActivityLog cree
        """
        actor_name = "Système"
        if actor:
            actor_name = actor.get_full_name() or actor.email

        try:
            activity = ActivityLog.objects.create(
                entity_type=entity_type,
                entity_id=entity_id,
                entity_name=entity_name,
                actor=actor,
                actor_name=actor_name,
                action=action,
                description=description,
                related_site=related_site,
                related_plan=related_plan,
                related_organisme=related_organisme,
                related_user=related_user,
                changes=changes or {},
                metadata=metadata or {},
                visibility=visibility
            )
            logger.debug(f"Activity logged: {activity}")
            return activity
        except Exception as e:
            logger.error(f"Failed to log activity: {e}")
            raise

    @staticmethod
    def log_site_activity(
        site: 'users.Site',
        action: str,
        actor: Optional['users.Role'],
        description: str,
        changes: Optional[dict] = None,
        metadata: Optional[dict] = None,
        visibility: str = 'public'
    ) -> ActivityLog:
        """
        Raccourci pour enregistrer une activite sur un site.

        Args:
            site: Le site concerne
            action: Type d'action
            actor: Acteur
            description: Description
            changes: Dict des changements
            metadata: Metadonnees
            visibility: Visibilite

        Returns:
            ActivityLog cree
        """
        # Recuperer l'organisme gestionnaire principal si disponible
        from apps.users.models import CorOgSite
        organisme = CorOgSite.get_principal(site)

        # Lors d'une suppression, ne pas lier le site (pre_delete : la FK sera cassée)
        related_site = None if action == 'delete' else site

        return ActivityService.log_activity(
            entity_type='site',
            entity_id=site.id_site,
            entity_name=site.nom_site,
            action=action,
            actor=actor,
            description=description,
            related_site=related_site,
            related_organisme=organisme,
            changes=changes,
            metadata=metadata,
            visibility=visibility
        )

    @staticmethod
    def log_plan_activity(
        plan: 'plans.PlanGestion',
        action: str,
        actor: Optional['users.Role'],
        description: str,
        changes: Optional[dict] = None,
        metadata: Optional[dict] = None,
        visibility: str = 'public'
    ) -> ActivityLog:
        """
        Raccourci pour enregistrer une activite sur un plan de gestion.

        Args:
            plan: Le plan concerne
            action: Type d'action
            actor: Acteur
            description: Description
            changes: Dict des changements
            metadata: Metadonnees
            visibility: Visibilite

        Returns:
            ActivityLog cree
        """
        # Recuperer le premier site lie au plan
        from apps.plans.models import CorSitePg
        site = None
        organisme = None
        cor_site_plan = CorSitePg.objects.filter(plan_de_gestion=plan).first()
        if cor_site_plan:
            site = cor_site_plan.site
            from apps.users.models import CorOgSite
            organisme = CorOgSite.get_principal(site)

        return ActivityService.log_activity(
            entity_type='plan',
            entity_id=plan.id_pg,
            entity_name=plan.nom,
            action=action,
            actor=actor,
            description=description,
            related_site=site,
            related_plan=plan,
            related_organisme=organisme,
            changes=changes,
            metadata=metadata,
            visibility=visibility
        )

    @staticmethod
    def log_user_activity(
        user: 'users.Role',
        action: str,
        actor: Optional['users.Role'],
        description: str,
        changes: Optional[dict] = None,
        metadata: Optional[dict] = None,
        visibility: str = 'public'
    ) -> ActivityLog:
        """
        Raccourci pour enregistrer une activite sur un utilisateur.

        Args:
            user: L'utilisateur concerne
            action: Type d'action
            actor: Acteur
            description: Description
            changes: Dict des changements
            metadata: Metadonnees
            visibility: Visibilite

        Returns:
            ActivityLog cree
        """
        return ActivityService.log_activity(
            entity_type='user',
            entity_id=user.id_role,
            entity_name=user.get_full_name() or user.email,
            action=action,
            actor=actor,
            description=description,
            related_organisme=user.id_organisme,
            related_user=user,
            changes=changes,
            metadata=metadata,
            visibility=visibility
        )

    @staticmethod
    def log_organisme_activity(
        organisme: 'users.BibOrganismes',
        action: str,
        actor: Optional['users.Role'],
        description: str,
        changes: Optional[dict] = None,
        metadata: Optional[dict] = None,
        visibility: str = 'public'
    ) -> ActivityLog:
        """
        Raccourci pour enregistrer une activite sur un organisme.

        Args:
            organisme: L'organisme concerne
            action: Type d'action
            actor: Acteur
            description: Description
            changes: Dict des changements
            metadata: Metadonnees
            visibility: Visibilite

        Returns:
            ActivityLog cree
        """
        return ActivityService.log_activity(
            entity_type='organisme',
            entity_id=organisme.id_organisme,
            entity_name=organisme.nom_organisme or f"Organisme {organisme.id_organisme}",
            action=action,
            actor=actor,
            description=description,
            related_organisme=organisme,
            changes=changes,
            metadata=metadata,
            visibility=visibility
        )

    @staticmethod
    def log_validation_activity(
        validation: 'notifications.ValidationRequest',
        action: str,
        actor: Optional['users.Role'],
        description: str,
        metadata: Optional[dict] = None,
        visibility: str = 'public'
    ) -> ActivityLog:
        """
        Raccourci pour enregistrer une activite sur une demande de validation.

        Args:
            validation: La demande de validation
            action: Type d'action
            actor: Acteur
            description: Description
            metadata: Metadonnees
            visibility: Visibilite

        Returns:
            ActivityLog cree
        """
        entity_name = validation.get_request_type_display()
        if validation.requester:
            entity_name += f" - {validation.requester.get_full_name()}"

        return ActivityService.log_activity(
            entity_type='validation',
            entity_id=validation.id,
            entity_name=entity_name,
            action=action,
            actor=actor,
            description=description,
            related_site=validation.target_site,
            related_plan=validation.target_plan,
            related_organisme=validation.requested_organisme,
            related_user=validation.requester,
            metadata=metadata,
            visibility=visibility
        )

    @staticmethod
    def log_rgpd_activity(
        user: 'users.Role',
        action: str,
        actor: Optional['users.Role'],
        description: str,
        metadata: Optional[dict] = None
    ) -> ActivityLog:
        """
        Raccourci pour enregistrer une activite RGPD.
        Ces activites sont visibles uniquement par les super_admin.

        Args:
            user: L'utilisateur concerne par l'action RGPD
            action: Type d'action RGPD (rgpd_request, rgpd_cancelled, rgpd_anonymized)
            actor: Acteur (l'utilisateur lui-meme ou un admin)
            description: Description
            metadata: Metadonnees

        Returns:
            ActivityLog cree
        """
        return ActivityService.log_user_activity(
            user=user,
            action=action,
            actor=actor,
            description=description,
            metadata=metadata,
            visibility='system'  # RGPD visible only to super_admin
        )

    @staticmethod
    def log_member_change(
        site: 'users.Site',
        user: 'users.Role',
        action: str,
        actor: Optional['users.Role'],
        is_referent: bool = False,
        metadata: Optional[dict] = None
    ) -> ActivityLog:
        """
        Enregistre l'ajout ou le retrait d'un membre d'un site.

        Args:
            site: Le site concerne
            user: L'utilisateur ajoute/retire
            action: 'add_member', 'remove_member', 'add_referent', 'remove_referent'
            actor: Acteur
            is_referent: Si l'utilisateur est/etait referent
            metadata: Metadonnees

        Returns:
            ActivityLog cree
        """
        action_labels = {
            'add_member': _("ajouté au site"),
            'remove_member': _("retiré du site"),
            'add_referent': _("nommé référent du site"),
            'remove_referent': _("retiré comme référent du site"),
        }

        user_name = user.get_full_name() or user.email
        description = f"{user_name} {action_labels.get(action, action)} {site.nom_site}"

        from apps.users.models import CorOgSite, Site
        organisme = CorOgSite.get_principal(site)

        # Si le site n'existe plus en base (CASCADE en cours), ne pas faire référence (FK sera cassée)
        related_site = site
        if not Site.objects.filter(pk=site.pk).exists():
            related_site = None

        return ActivityService.log_activity(
            entity_type='site',
            entity_id=site.id_site,
            entity_name=site.nom_site,
            action=action,
            actor=actor,
            description=description,
            related_site=related_site,
            related_organisme=organisme,
            related_user=user,
            metadata={
                **(metadata or {}),
                'member_id': user.id_role,
                'member_name': user_name,
                'is_referent': is_referent
            }
        )

    @staticmethod
    def log_plan_referent_change(
        plan: 'plans.PlanGestion',
        user: 'users.Role',
        action: str,
        actor: Optional['users.Role'],
        metadata: Optional[dict] = None
    ) -> ActivityLog:
        """
        Enregistre l'ajout ou le retrait d'un referent d'un plan.

        Args:
            plan: Le plan concerne
            user: L'utilisateur ajoute/retire
            action: 'add_referent' ou 'remove_referent'
            actor: Acteur
            metadata: Metadonnees

        Returns:
            ActivityLog cree
        """
        user_name = user.get_full_name() or user.email
        action_label = "nommé référent" if action == 'add_referent' else "retiré comme référent"
        description = f"{user_name} {action_label} du plan {plan.nom}"

        # Recuperer le premier site lie
        from apps.plans.models import CorSitePg
        site = None
        organisme = None
        cor_site_plan = CorSitePg.objects.filter(plan_de_gestion=plan).first()
        if cor_site_plan:
            site = cor_site_plan.site
            from apps.users.models import CorOgSite
            organisme = CorOgSite.get_principal(site)

        return ActivityService.log_activity(
            entity_type='plan',
            entity_id=plan.id_pg,
            entity_name=plan.nom,
            action=action,
            actor=actor,
            description=description,
            related_site=site,
            related_plan=plan,
            related_organisme=organisme,
            related_user=user,
            metadata={
                **(metadata or {}),
                'referent_id': user.id_role,
                'referent_name': user_name
            }
        )

    @staticmethod
    def get_model_changes(old_instance: Model, new_data: dict, fields: list[str]) -> dict:
        """
        Compare une instance avec de nouvelles donnees et retourne les changements.

        Args:
            old_instance: Instance avant modification
            new_data: Nouvelles valeurs (dict)
            fields: Liste des champs a comparer

        Returns:
            Dict des changements {field: {old, new}}
        """
        changes = {}
        for field in fields:
            old_value = getattr(old_instance, field, None)
            new_value = new_data.get(field)

            # Convertir en valeurs comparables
            if hasattr(old_value, 'pk'):
                old_value = old_value.pk
            if hasattr(new_value, 'pk'):
                new_value = new_value.pk

            # Ne garder que les vrais changements
            if old_value != new_value and new_value is not None:
                changes[field] = {
                    'old': str(old_value) if old_value is not None else None,
                    'new': str(new_value) if new_value is not None else None
                }

        return changes
