"""Serializers pour l'API INPG (géologie)."""

from rest_framework import serializers

from .models import Inpg


class InpgDetailSerializer(serializers.ModelSerializer):
    """Serializer complet pour le détail d'un site INPG."""

    class Meta:
        model = Inpg
        fields = '__all__'


class InpgListSerializer(serializers.ModelSerializer):
    """Serializer allégé pour la liste des sites INPG."""

    class Meta:
        model = Inpg
        fields = [
            'id_inpg', 'id_metier', 'lb_site', 'region',
            'departements', 'communes', 'interet_geol_principal',
            'typologie_1', 'nombre_etoiles',
        ]
