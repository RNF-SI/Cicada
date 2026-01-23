"""
Serializers pour les modeles du core.
"""
from rest_framework import serializers

from .models import Module, ErrorLog, ActivityLog, SiteConfiguration


# =============================================================================
# SiteConfiguration Serializers
# =============================================================================

class SiteConfigurationSerializer(serializers.ModelSerializer):
    """
    Serializer pour la lecture de la configuration du site.
    Retourne des URLs relatives pour compatibilite avec le proxy frontend.
    """

    # Override homepage_image to return relative path instead of full URL
    homepage_image = serializers.SerializerMethodField()
    homepage_image_url = serializers.SerializerMethodField()
    updated_by_name = serializers.SerializerMethodField()

    class Meta:
        model = SiteConfiguration
        fields = [
            'homepage_image',
            'homepage_image_url',
            'updated_at',
            'updated_by',
            'updated_by_name',
        ]
        read_only_fields = fields

    def get_homepage_image(self, obj) -> str | None:
        """Retourne le chemin relatif de l'image (sans le domaine)."""
        if obj.homepage_image:
            return obj.homepage_image.name
        return None

    def get_homepage_image_url(self, obj) -> str | None:
        """Retourne l'URL relative de l'image (compatible avec le proxy frontend)."""
        if obj.homepage_image:
            # Return relative URL to work with Angular proxy
            return obj.homepage_image.url
        return None

    def get_updated_by_name(self, obj) -> str | None:
        """Retourne le nom de l'utilisateur qui a fait la derniere modification."""
        if obj.updated_by:
            return obj.updated_by.get_full_name() or obj.updated_by.email
        return None


class SiteConfigurationUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer pour la mise a jour de la configuration du site.
    Accepte l'upload d'image.
    """

    class Meta:
        model = SiteConfiguration
        fields = ['homepage_image']


class ModuleSerializer(serializers.ModelSerializer):
    """
    Serializer complet pour le modele Module.
    """

    color_display = serializers.CharField(
        source='get_color_display',
        read_only=True
    )

    class Meta:
        model = Module
        fields = [
            'id',
            'code',
            'name',
            'description',
            'icon',
            'color',
            'color_display',
            'route',
            'requires_access',
            'is_active',
            'display_order',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class ModuleListSerializer(serializers.ModelSerializer):
    """
    Serializer simplifie pour les listes de modules.
    Utilise par le frontend pour afficher les tuiles.
    """

    class Meta:
        model = Module
        fields = [
            'id',
            'code',
            'name',
            'description',
            'icon',
            'color',
            'route',
            'requires_access',
            'display_order',
        ]


class ModuleCreateUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer pour la creation et mise a jour des modules.
    """

    class Meta:
        model = Module
        fields = [
            'code',
            'name',
            'description',
            'icon',
            'color',
            'route',
            'requires_access',
            'is_active',
            'display_order',
        ]

    def validate_code(self, value):
        """Valide que le code est en minuscules et sans espaces."""
        code = value.lower().strip().replace(' ', '_')
        return code

    def validate_route(self, value):
        """Valide que la route commence par /."""
        if not value.startswith('/'):
            value = '/' + value
        return value


# =============================================================================
# ErrorLog Serializers
# =============================================================================

class ErrorLogListSerializer(serializers.ModelSerializer):
    """
    Serializer pour la liste des logs d'erreur.
    Version simplifiee pour le tableau.
    """

    user_name = serializers.SerializerMethodField()
    acknowledged_by_name = serializers.SerializerMethodField()
    level_display = serializers.CharField(source='get_level_display', read_only=True)

    class Meta:
        model = ErrorLog
        fields = [
            'id',
            'level',
            'level_display',
            'message',
            'logger_name',
            'correlation_id',
            'user',
            'user_name',
            'path',
            'method',
            'exception_type',
            'acknowledged',
            'acknowledged_by',
            'acknowledged_by_name',
            'acknowledged_at',
            'created_at',
        ]
        read_only_fields = fields

    def get_user_name(self, obj) -> str | None:
        if obj.user:
            return f"{obj.user.prenom_role or ''} {obj.user.nom_role or ''}".strip() or obj.user.email
        return None

    def get_acknowledged_by_name(self, obj) -> str | None:
        if obj.acknowledged_by:
            return f"{obj.acknowledged_by.prenom_role or ''} {obj.acknowledged_by.nom_role or ''}".strip() or obj.acknowledged_by.email
        return None


class ErrorLogDetailSerializer(serializers.ModelSerializer):
    """
    Serializer complet pour le detail d'un log d'erreur.
    Inclut le stack trace et le contexte.
    """

    user_name = serializers.SerializerMethodField()
    user_email = serializers.SerializerMethodField()
    acknowledged_by_name = serializers.SerializerMethodField()
    level_display = serializers.CharField(source='get_level_display', read_only=True)

    class Meta:
        model = ErrorLog
        fields = [
            'id',
            'level',
            'level_display',
            'message',
            'logger_name',
            'correlation_id',
            'user',
            'user_name',
            'user_email',
            'path',
            'method',
            'exception_type',
            'stack_trace',
            'context',
            'acknowledged',
            'acknowledged_by',
            'acknowledged_by_name',
            'acknowledged_at',
            'created_at',
        ]
        read_only_fields = fields

    def get_user_name(self, obj) -> str | None:
        if obj.user:
            return f"{obj.user.prenom_role or ''} {obj.user.nom_role or ''}".strip() or obj.user.email
        return None

    def get_user_email(self, obj) -> str | None:
        if obj.user:
            return obj.user.email
        return None

    def get_acknowledged_by_name(self, obj) -> str | None:
        if obj.acknowledged_by:
            return f"{obj.acknowledged_by.prenom_role or ''} {obj.acknowledged_by.nom_role or ''}".strip() or obj.acknowledged_by.email
        return None


class ErrorLogStatsSerializer(serializers.Serializer):
    """Serializer pour les statistiques des logs d'erreur."""

    total = serializers.IntegerField()
    unacknowledged = serializers.IntegerField()
    by_level = serializers.DictField(child=serializers.IntegerField())
    by_day = serializers.ListField(child=serializers.DictField())


# =============================================================================
# ActivityLog Serializers
# =============================================================================

class ActivityLogListSerializer(serializers.ModelSerializer):
    """
    Serializer pour la liste des logs d'activite.
    Optimise pour la timeline avec informations essentielles.
    """

    entity_type_display = serializers.CharField(
        source='get_entity_type_display',
        read_only=True
    )
    action_display = serializers.CharField(
        source='get_action_display',
        read_only=True
    )

    # Relations simplifiees
    related_site_name = serializers.SerializerMethodField()
    related_site_slug = serializers.SerializerMethodField()
    related_plan_name = serializers.SerializerMethodField()
    related_organisme_name = serializers.SerializerMethodField()
    related_user_name = serializers.SerializerMethodField()

    class Meta:
        model = ActivityLog
        fields = [
            'id',
            'entity_type',
            'entity_type_display',
            'entity_id',
            'entity_name',
            'actor_name',
            'action',
            'action_display',
            'description',
            'related_site',
            'related_site_name',
            'related_site_slug',
            'related_plan',
            'related_plan_name',
            'related_organisme',
            'related_organisme_name',
            'related_user',
            'related_user_name',
            'visibility',
            'created_at',
        ]
        read_only_fields = fields

    def get_related_site_name(self, obj) -> str | None:
        if obj.related_site:
            return obj.related_site.nom_site
        return None

    def get_related_site_slug(self, obj) -> str | None:
        if obj.related_site:
            return obj.related_site.slug
        return None

    def get_related_plan_name(self, obj) -> str | None:
        if obj.related_plan:
            return obj.related_plan.nom
        return None

    def get_related_organisme_name(self, obj) -> str | None:
        if obj.related_organisme:
            return obj.related_organisme.nom_organisme
        return None

    def get_related_user_name(self, obj) -> str | None:
        if obj.related_user:
            return obj.related_user.get_full_name() or obj.related_user.email
        return None


class ActivityLogDetailSerializer(serializers.ModelSerializer):
    """
    Serializer complet pour le detail d'une activite.
    Inclut les changements et metadonnees.
    """

    entity_type_display = serializers.CharField(
        source='get_entity_type_display',
        read_only=True
    )
    action_display = serializers.CharField(
        source='get_action_display',
        read_only=True
    )
    visibility_display = serializers.CharField(
        source='get_visibility_display',
        read_only=True
    )

    # Relations simplifiees
    related_site_name = serializers.SerializerMethodField()
    related_site_slug = serializers.SerializerMethodField()
    related_plan_name = serializers.SerializerMethodField()
    related_organisme_name = serializers.SerializerMethodField()
    related_user_name = serializers.SerializerMethodField()
    actor_email = serializers.SerializerMethodField()

    class Meta:
        model = ActivityLog
        fields = [
            'id',
            'entity_type',
            'entity_type_display',
            'entity_id',
            'entity_name',
            'actor',
            'actor_name',
            'actor_email',
            'action',
            'action_display',
            'description',
            'related_site',
            'related_site_name',
            'related_site_slug',
            'related_plan',
            'related_plan_name',
            'related_organisme',
            'related_organisme_name',
            'related_user',
            'related_user_name',
            'changes',
            'metadata',
            'visibility',
            'visibility_display',
            'created_at',
        ]
        read_only_fields = fields

    def get_related_site_name(self, obj) -> str | None:
        if obj.related_site:
            return obj.related_site.nom_site
        return None

    def get_related_site_slug(self, obj) -> str | None:
        if obj.related_site:
            return obj.related_site.slug
        return None

    def get_related_plan_name(self, obj) -> str | None:
        if obj.related_plan:
            return obj.related_plan.nom
        return None

    def get_related_organisme_name(self, obj) -> str | None:
        if obj.related_organisme:
            return obj.related_organisme.nom_organisme
        return None

    def get_related_user_name(self, obj) -> str | None:
        if obj.related_user:
            return obj.related_user.get_full_name() or obj.related_user.email
        return None

    def get_actor_email(self, obj) -> str | None:
        if obj.actor:
            return obj.actor.email
        return None


class ActivityLogStatsSerializer(serializers.Serializer):
    """Serializer pour les statistiques des logs d'activite."""

    total = serializers.IntegerField()
    by_type = serializers.DictField(child=serializers.IntegerField())
    by_action = serializers.DictField(child=serializers.IntegerField())
    by_day = serializers.ListField(child=serializers.DictField())
