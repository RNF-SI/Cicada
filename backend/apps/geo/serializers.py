"""Sérialiseurs du référentiel géographique administratif."""

from rest_framework import serializers

from .models import LArea


class DepartementSerializer(serializers.ModelSerializer):
    """Département, sans sa géométrie (inutile pour un filtre)."""

    code = serializers.CharField(source='area_code')
    nom = serializers.CharField(source='area_name')

    class Meta:
        model = LArea
        fields = ['id_area', 'code', 'nom']


class RegionSerializer(serializers.ModelSerializer):
    """Région et ses départements — alimente l'arbre « zone géographique »."""

    code = serializers.CharField(source='area_code')
    nom = serializers.CharField(source='area_name')
    departements = serializers.SerializerMethodField()

    class Meta:
        model = LArea
        fields = ['id_area', 'code', 'nom', 'departements']

    def get_departements(self, obj):
        # `children` est préchargé par la vue : pas de requête par région.
        enfants = sorted(obj.children.all(), key=lambda a: a.area_code)
        return DepartementSerializer(enfants, many=True).data
