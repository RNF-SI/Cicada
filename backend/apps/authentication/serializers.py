"""
Serializers pour l'authentification.
"""
from django.contrib.auth import authenticate
from django.db.models import Q
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken
from apps.users.models import Role


class CustomTokenObtainPairSerializer(serializers.Serializer):
    """
    Serializer personnalise pour l'obtention de tokens JWT.
    Accepte soit un email soit un identifiant (pseudo) pour la connexion.
    """

    username = serializers.CharField(
        write_only=True,
        help_text="Email ou identifiant de l'utilisateur"
    )
    password = serializers.CharField(
        write_only=True,
        style={'input_type': 'password'}
    )

    def validate(self, attrs):
        username = attrs.get('username')
        password = attrs.get('password')

        if not username or not password:
            raise serializers.ValidationError(
                "L'identifiant et le mot de passe sont requis."
            )

        # Rechercher l'utilisateur par email OU identifiant
        user = Role.objects.filter(
            Q(email__iexact=username) | Q(identifiant__iexact=username)
        ).first()

        if not user:
            raise serializers.ValidationError(
                "Identifiant ou mot de passe incorrect."
            )

        # Verifier le mot de passe
        if not user.check_password(password):
            raise serializers.ValidationError(
                "Identifiant ou mot de passe incorrect."
            )

        # Verifier que l'utilisateur est actif
        if not user.active or not user.is_active:
            raise serializers.ValidationError(
                "Ce compte est desactive."
            )

        # Generer les tokens JWT
        refresh = RefreshToken.for_user(user)

        # Stocker l'utilisateur pour l'utiliser dans la reponse
        self.user = user

        return {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'user': {
                'id': user.id_role,
                'email': user.email,
                'nom_role': user.nom_role,
                'prenom_role': user.prenom_role,
                'identifiant': user.identifiant,
                'niveau_role': user.role_level,
                'is_staff': user.is_staff,
                'is_active': user.active,
                'organisme': {
                    'id': user.id_organisme.id_organisme,
                    'nom_organisme': user.id_organisme.nom_organisme,
                } if user.id_organisme else None
            }
        }


class UserInfoSerializer(serializers.ModelSerializer):
    """
    Serializer pour les informations utilisateur.
    """

    id = serializers.IntegerField(source='id_role', read_only=True)
    niveau_role = serializers.CharField(source='role_level', read_only=True)
    is_active = serializers.BooleanField(source='active', read_only=True)
    organisme = serializers.SerializerMethodField()

    class Meta:
        model = Role
        fields = [
            'id', 'email', 'nom_role', 'prenom_role', 'identifiant',
            'niveau_role', 'is_staff', 'is_active', 'organisme',
            'date_insert', 'last_login'
        ]
        read_only_fields = ['id', 'date_insert', 'last_login']

    def get_organisme(self, obj):
        """Retourne les informations de l'organisme."""
        if obj.id_organisme:
            return {
                'id': obj.id_organisme.id_organisme,
                'nom_organisme': obj.id_organisme.nom_organisme,
                'ville_organisme': obj.id_organisme.ville_organisme
            }
        return None
