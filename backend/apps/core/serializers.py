"""
Serializers pour les modeles du core.
"""
from rest_framework import serializers

from .models import Module


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
