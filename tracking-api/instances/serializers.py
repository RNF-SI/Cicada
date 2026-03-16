"""
Serializers pour l'API de suivi
"""
from rest_framework import serializers
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
