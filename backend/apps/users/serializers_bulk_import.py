"""
Serializers pour l'import en masse de sites.
"""
from rest_framework import serializers


class BulkSiteRowSerializer(serializers.Serializer):
    """Valide une ligne de données de site pour l'import en masse."""

    nom_site = serializers.CharField(required=True, min_length=3, max_length=255)
    id_local = serializers.CharField(required=False, allow_blank=True, allow_null=True, max_length=50)
    id_inpn = serializers.CharField(required=False, allow_blank=True, allow_null=True, max_length=50)
    type_site_id = serializers.IntegerField(required=False, allow_null=True)
    surf_off = serializers.FloatField(required=False, allow_null=True, min_value=0)
    marin = serializers.BooleanField(required=False, default=False)
    outre_mer = serializers.BooleanField(required=False, default=False)
    geom_geojson = serializers.JSONField(required=False, allow_null=True)
    geom_pt_geojson = serializers.JSONField(required=False, allow_null=True)


class BulkSiteValidateResponseSerializer(serializers.Serializer):
    """Réponse de validation d'import en masse."""

    detected_properties = serializers.ListField(child=serializers.CharField())
    suggested_mapping = serializers.DictField(child=serializers.CharField())
    sites = serializers.ListField()
    total = serializers.IntegerField()
    valid = serializers.IntegerField()
    errors = serializers.IntegerField()
    warnings = serializers.IntegerField()
    duplicates = serializers.IntegerField()


class BulkSiteImportExecuteSerializer(serializers.Serializer):
    """Payload pour exécuter l'import en masse."""

    sites = serializers.ListField(child=serializers.DictField(), required=True)
    selected_indices = serializers.ListField(child=serializers.IntegerField(), required=True)
    field_mapping = serializers.DictField(child=serializers.CharField(), required=False)
