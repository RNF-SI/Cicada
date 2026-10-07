"""
Serializers pour l'API de suivi
"""
from rest_framework import serializers
from .adhesion import REGEX_EMPREINTE, REGEX_IDENTIFIANT
from .models import Instance


class InstanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Instance
        fields = '__all__'
        read_only_fields = ('token', 'first_seen', 'created_at', 'updated_at')

    def to_representation(self, instance):
        """Masque les données personnelles si pas de consentement"""
        data = super().to_representation(instance)
        
        # Si pas de consentement RGPD, masquer les données nominatives
        if not instance.rgpd_consent:
            data['admin_name'] = None
            data['admin_email'] = None
            data['structure_name'] = None
        
        return data


class DemandeAdhesionSerializer(serializers.Serializer):
    """Corps de POST /instances/adhesion-hub/ — mêmes règles que le hub (#696).

    Valider ici ce que le hub validera évite qu'un admin RNF accepte une demande
    que le hub rejetterait ensuite en 400 : l'erreur revient tout de suite à la
    structure, qui peut la corriger.
    """
    instance_id = serializers.RegexField(REGEX_IDENTIFIANT, max_length=50)
    libelle = serializers.CharField(max_length=200)
    url_publique = serializers.URLField(max_length=500, required=False, allow_blank=True, default='')
    empreinte_depot = serializers.RegexField(REGEX_EMPREINTE)
    empreinte_lecture = serializers.RegexField(REGEX_EMPREINTE)

    def validate(self, data):
        # Deux jetons identiques ne seraient plus deux droits distincts.
        if data['empreinte_depot'] == data['empreinte_lecture']:
            raise serializers.ValidationError("Les jetons de dépôt et de lecture doivent être distincts.")
        return data
