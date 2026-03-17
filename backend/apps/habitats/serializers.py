"""Serializers pour l'API HabRef."""

from rest_framework import serializers

from .models import Habref, Typoref, AutocompleteHabitat, HabrefCorrespHab


class HabrefDetailSerializer(serializers.ModelSerializer):
    """Serializer complet pour le détail d'un habitat."""

    class Meta:
        model = Habref
        fields = '__all__'


class TyporefSerializer(serializers.ModelSerializer):
    """Serializer pour les typologies d'habitats."""

    class Meta:
        model = Typoref
        fields = '__all__'


class AutocompleteHabitatSerializer(serializers.ModelSerializer):
    """Serializer pour l'autocomplete des habitats."""

    class Meta:
        model = AutocompleteHabitat
        fields = [
            'cd_hab', 'cd_typo', 'lb_code', 'search_name',
            'lb_hab_fr', 'lb_hab_fr_complet', 'lb_typo', 'niveau',
        ]


class HabrefCorrespHabSerializer(serializers.ModelSerializer):
    """Serializer pour les correspondances entre habitats."""

    class Meta:
        model = HabrefCorrespHab
        fields = '__all__'
