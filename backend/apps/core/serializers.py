"""
Serializers pour les modeles du core.
"""
from rest_framework import serializers

from .models import Module, ErrorLog


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
