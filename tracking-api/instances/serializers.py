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
    # Personne que RNF appellera, et à qui le code sera (a priori) envoyé.
    contact_nom = serializers.CharField(max_length=200)
    contact_email = serializers.EmailField()
    contact_telephone = serializers.CharField(max_length=50, required=False, allow_blank=True, default='')
    message = serializers.CharField(max_length=5000, required=False, allow_blank=True, default='')

    def validate(self, data):
        # Deux jetons identiques ne seraient plus deux droits distincts.
        if data['empreinte_depot'] == data['empreinte_lecture']:
            raise serializers.ValidationError("Les jetons de dépôt et de lecture doivent être distincts.")
        return data


class ConfirmationSerializer(serializers.Serializer):
    """Corps de POST /instances/adhesion-hub/confirmation/. Vide = code faux, pas erreur de format."""
    code = serializers.CharField(max_length=50, required=False, allow_blank=True, default='')


class ContactSerializer(serializers.Serializer):
    """Corps de POST /instances/contact/ : message libre d'un administrateur d'instance à RNF."""
    nom = serializers.CharField(max_length=200)
    email = serializers.EmailField()
    sujet = serializers.CharField(max_length=200)
    message = serializers.CharField(max_length=5000)

    def validate_sujet(self, valeur):
        # Le sujet finit dans un en-tête d'e-mail : un saut de ligne y serait
        # refusé par Django (BadHeaderError), autant l'aplatir.
        return ' '.join(valeur.split())
