"""
Serializers pour l'authentification.
"""
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from apps.users.models import Role


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Serializer personnalisé pour l'obtention de tokens JWT.
    Utilise l'email au lieu du username par défaut.
    """
    
    username_field = 'email'
    
    def validate(self, attrs):
        # Utilise l'email comme identifiant
        data = super().validate(attrs)
        
        # Ajoute des informations utilisateur dans la réponse
        data.update({
            'user': {
                'id': self.user.id_role,
                'email': self.user.email,
                'nom': self.user.nom_role,
                'prenom': self.user.prenom_role,
                'is_staff': self.user.is_staff,
                'organisme': {
                    'id': self.user.id_organisme.id_organisme if self.user.id_organisme else None,
                    'nom': self.user.id_organisme.nom_organisme if self.user.id_organisme else None,
                } if self.user.id_organisme else None
            }
        })
        
        return data


class UserInfoSerializer(serializers.ModelSerializer):
    """
    Serializer pour les informations utilisateur.
    """
    
    organisme = serializers.SerializerMethodField()
    
    class Meta:
        model = Role
        fields = [
            'id_role', 'email', 'nom_role', 'prenom_role', 
            'is_staff', 'is_superuser', 'active', 'organisme',
            'date_insert', 'last_login'
        ]
        read_only_fields = ['id_role', 'date_insert', 'last_login']
    
    def get_organisme(self, obj):
        """Retourne les informations de l'organisme."""
        if obj.id_organisme:
            return {
                'id': obj.id_organisme.id_organisme,
                'nom': obj.id_organisme.nom_organisme,
                'ville': obj.id_organisme.ville_organisme
            }
        return None