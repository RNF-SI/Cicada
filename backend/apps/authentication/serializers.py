"""
Serializers pour l'authentification.
"""
from django.contrib.auth import authenticate
from django.contrib.auth.models import update_last_login
from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework_simplejwt.settings import api_settings as jwt_api_settings
from rest_framework_simplejwt.tokens import RefreshToken
from apps.users.models import Role


class CustomTokenObtainPairSerializer(serializers.Serializer):
    """
    Serializer personnalise pour l'obtention de tokens JWT.
    Accepte soit un email soit un identifiant (pseudo) pour la connexion.
    """

    username = serializers.CharField(
        write_only=True,
        help_text=_("Email ou identifiant de l'utilisateur")
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
                _("L'identifiant et le mot de passe sont requis.")
            )

        # Rechercher l'utilisateur par email OU identifiant
        user = Role.objects.filter(
            Q(email__iexact=username) | Q(identifiant__iexact=username)
        ).first()

        if not user:
            # Verifier si c'est un utilisateur en attente d'inscription
            from apps.notifications.models import PendingUser
            pending = PendingUser.objects.filter(email__iexact=username).first()
            if pending:
                # Determiner qui doit valider
                if pending.requested_organisme:
                    validator_info = f"un administrateur de {pending.requested_organisme.nom_organisme}"
                else:
                    validator_info = _("un administrateur")
                raise serializers.ValidationError(
                    _("Votre demande d'inscription est en attente de validation par %(validator)s. "
                      "Vous recevrez un email lorsque votre compte sera activé.") % {'validator': validator_info}
                )
            raise serializers.ValidationError(
                _("Identifiant ou mot de passe incorrect.")
            )

        # Verifier le mot de passe
        if not user.check_password(password):
            raise serializers.ValidationError(
                _("Identifiant ou mot de passe incorrect.")
            )

        # Verifier que l'utilisateur est actif
        if not user.active or not user.is_active:
            raise serializers.ValidationError(
                _("Ce compte est désactivé.")
            )

        # Verifier si l'utilisateur est en attente de validation
        if user.pending_validation:
            # Determiner qui doit valider
            if user.id_organisme:
                validator_info = f"un administrateur de {user.id_organisme.nom_organisme}"
            else:
                validator_info = _("un administrateur")
            raise serializers.ValidationError(
                _("Votre compte est en attente de validation par %(validator)s. "
                  "Vous recevrez un email lorsque votre compte sera activé.") % {'validator': validator_info}
            )

        # Generer les tokens JWT
        refresh = RefreshToken.for_user(user)

        # Mettre a jour last_login (le custom serializer ne passe pas par
        # le flow standard simplejwt qui le fait automatiquement)
        if jwt_api_settings.UPDATE_LAST_LOGIN:
            update_last_login(None, user)

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
                'is_referent': user.is_referent(),
                'organisme': {
                    'id_organisme': user.id_organisme.id_organisme,
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
    is_referent = serializers.SerializerMethodField()
    organisme = serializers.SerializerMethodField()

    class Meta:
        model = Role
        fields = [
            'id', 'email', 'nom_role', 'prenom_role', 'identifiant',
            'niveau_role', 'is_staff', 'is_active', 'is_referent', 'organisme',
            'date_insert', 'last_login'
        ]
        read_only_fields = ['id', 'date_insert', 'last_login']

    def get_is_referent(self, obj):
        """Retourne True si l'utilisateur est referent d'au moins un site ou plan."""
        return obj.is_referent()

    def get_organisme(self, obj):
        """Retourne les informations de l'organisme."""
        if obj.id_organisme:
            return {
                'id_organisme': obj.id_organisme.id_organisme,
                'nom_organisme': obj.id_organisme.nom_organisme,
                'ville_organisme': obj.id_organisme.ville_organisme
            }
        return None
