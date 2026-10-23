"""
Vues pour l'authentification JWT.
"""
import logging

from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import (
    OpenApiParameter,
    OpenApiResponse,
    extend_schema,
    inline_serializer,
)
from rest_framework import serializers, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenRefreshView

from .throttles import AuthRateThrottle
from rest_framework_simplejwt.tokens import RefreshToken, AccessToken
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken

from apps.users.models import Role, Site, BibOrganismes
from apps.plans.models import PlanGestion
from .models import ImpersonationLog
from .providers import ConnexionLocaleActive, GEONATURE, mode_connexion, usershub
from .serializers import (
    reponse_connexion,
    CustomTokenObtainPairSerializer,
    DetailSchema,
    JetonsConnexionSchema,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    ProfilConnexionSchema,
    UserInfoSerializer,
)

logger = logging.getLogger(__name__)

# Réponses d'erreur communes (documentation OpenAPI)
REPONSE_401 = OpenApiResponse(response=DetailSchema, description="Jeton absent, invalide ou expiré.")
REPONSE_403 = OpenApiResponse(response=DetailSchema, description="Droits insuffisants.")
REPONSE_403_CONNEXION_EXTERNE = OpenApiResponse(
    response=DetailSchema,
    description="Instance en mode de connexion GeoNature : la connexion locale, "
                "l'inscription et le mot de passe oublié sont fermés (#689).",
)
REPONSE_429 = OpenApiResponse(description="Trop de tentatives : limitation de débit sur l'authentification.")


class CustomTokenObtainPairView(APIView):
    """
    Vue personnalisee pour obtenir les tokens JWT.
    Accepte soit un email soit un identifiant (pseudo) pour la connexion.

    POST /api/auth/login/
    Body: {"username": "email_ou_identifiant", "password": "mot_de_passe"}
    """
    permission_classes = [ConnexionLocaleActive]
    throttle_classes = [AuthRateThrottle]

    @extend_schema(
        tags=['auth'],
        summary="Connexion avec un compte CICADA",
        description=(
            "Obtient une paire de jetons JWT à partir d'un email **ou** d'un identifiant "
            "et du mot de passe. Public. Disponible uniquement quand l'instance est en "
            "connexion locale (voir `GET /api/auth/mode/`). Un compte en attente de "
            "validation ou désactivé est refusé en 401 avec un message explicite."
        ),
        request=CustomTokenObtainPairSerializer,
        responses={
            200: JetonsConnexionSchema,
            400: OpenApiResponse(
                response=inline_serializer(
                    name='ErreursConnexion',
                    fields={
                        'detail': serializers.CharField(),
                        'errors': serializers.DictField(child=serializers.ListField(child=serializers.CharField())),
                    },
                ),
                description="Champs manquants ou invalides (erreurs par champ).",
            ),
            401: OpenApiResponse(response=DetailSchema, description="Identifiants incorrects, compte désactivé ou en attente de validation."),
            403: REPONSE_403_CONNEXION_EXTERNE,
            429: REPONSE_429,
        },
    )
    def post(self, request):
        serializer = CustomTokenObtainPairSerializer(data=request.data)

        if serializer.is_valid():
            return Response(serializer.validated_data, status=status.HTTP_200_OK)

        # Reformater les erreurs pour un message plus clair
        errors = serializer.errors
        if 'non_field_errors' in errors:
            return Response(
                {'detail': errors['non_field_errors'][0]},
                status=status.HTTP_401_UNAUTHORIZED
            )

        return Response(
            {'detail': 'Donnees invalides', 'errors': errors},
            status=status.HTTP_400_BAD_REQUEST
        )


class ModeConnexionView(APIView):
    """
    Mode de connexion de l'instance (#689) — un seul à la fois.

    GET /api/auth/mode/  →  {"mode": "local"}  ou  {"mode": "geonature", "libelle": "RNF"}
    Public : la page de connexion l'appelle avant toute authentification.
    """
    permission_classes = [AllowAny]

    @extend_schema(
        tags=['auth'],
        summary="Mode de connexion de l'instance",
        description=(
            "Indique si l'instance accepte les comptes CICADA (`local`) ou les comptes "
            "GeoNature / UsersHub (`geonature`, avec le libellé à afficher). Public : "
            "la page de connexion l'appelle avant toute authentification (#689)."
        ),
        auth=[],
        responses={
            200: inline_serializer(
                name='ModeConnexion',
                fields={
                    'mode': serializers.ChoiceField(choices=['local', 'geonature']),
                    'libelle': serializers.CharField(required=False, help_text="Nom de l'annuaire GeoNature (mode geonature seulement)"),
                },
            ),
        },
    )
    def get(self, request):
        if mode_connexion() == GEONATURE:
            return Response({'mode': GEONATURE, 'libelle': settings.GEONATURE_AUTH_LIBELLE})
        return Response({'mode': 'local'})


class ConnexionGeoNatureView(APIView):
    """
    Connexion avec un compte GeoNature / UsersHub (#689, #691).

    POST /api/auth/login-geonature/
    Body: {"login": "identifiant UsersHub", "password": "…"}

    Renvoie les mêmes jetons que POST /api/auth/login/.
    """
    permission_classes = [AllowAny]
    throttle_classes = [AuthRateThrottle]

    @extend_schema(
        tags=['auth'],
        summary="Connexion avec un compte GeoNature / UsersHub",
        description=(
            "Authentifie l'utilisateur auprès de l'annuaire UsersHub de l'instance, crée ou "
            "met à jour son compte CICADA, et renvoie les mêmes jetons que "
            "`POST /api/auth/login/`. Public. Répond 404 si l'instance n'est pas en mode "
            "`geonature` (#689, #691)."
        ),
        request=inline_serializer(
            name='ConnexionGeoNature',
            fields={
                'login': serializers.CharField(help_text="Identifiant UsersHub"),
                'password': serializers.CharField(style={'input_type': 'password'}),
            },
        ),
        responses={
            200: JetonsConnexionSchema,
            400: OpenApiResponse(response=DetailSchema, description="Identifiant ou mot de passe manquant."),
            401: OpenApiResponse(response=DetailSchema, description="Identifiants refusés par UsersHub."),
            403: OpenApiResponse(response=DetailSchema, description="Compte désactivé, sans email, ou sans accès à l'application CICADA (source 'base', #764)."),
            404: OpenApiResponse(response=DetailSchema, description="Connexion GeoNature non activée sur cette instance."),
            429: REPONSE_429,
            503: OpenApiResponse(response=DetailSchema, description="Annuaire GeoNature non configuré ou injoignable."),
        },
    )
    def post(self, request):
        if mode_connexion() != GEONATURE:
            return Response({'detail': "Connexion GeoNature non activée sur cette instance."},
                            status=status.HTTP_404_NOT_FOUND)
        if not usershub.est_active():
            logger.error("AUTH_PROVIDER=geonature sans les réglages de sa source (GEONATURE_AUTH_SOURCE=%s)",
                         settings.GEONATURE_AUTH_SOURCE)
            return Response({'detail': "La connexion n'est pas configurée sur cette instance. "
                                       "Contactez son administrateur."},
                            status=status.HTTP_503_SERVICE_UNAVAILABLE)

        login = (request.data.get('login') or '').strip()
        password = request.data.get('password') or ''
        if not login or not password:
            return Response({'detail': "L'identifiant et le mot de passe sont requis."},
                            status=status.HTTP_400_BAD_REQUEST)

        try:
            identite = usershub.verifier(login, password)
            compte = usershub.compte_pour(identite)
        except usershub.UsersHubErreur as exc:
            return Response({'detail': str(exc.message)}, status=exc.status_code)

        return Response(reponse_connexion(compte), status=status.HTTP_200_OK)


class CustomTokenRefreshView(TokenRefreshView):
    """
    Vue personnalisee pour le refresh de token JWT.
    Verifie que l'utilisateur est toujours actif avant de generer un nouveau token.

    POST /api/auth/refresh/
    Body: {"refresh": "refresh_token"}
    """

    @extend_schema(
        tags=['auth'],
        summary="Rafraîchir le jeton d'accès",
        description=(
            "Échange un jeton de rafraîchissement valide contre un nouveau jeton d'accès. "
            "Refusé (401) si le compte a été désactivé ou supprimé entre-temps."
        ),
        responses={
            200: OpenApiResponse(description="Nouveau jeton d'accès (`access`) et, selon la rotation configurée, nouveau `refresh`."),
            401: OpenApiResponse(response=DetailSchema, description="Jeton de rafraîchissement invalide, expiré ou compte désactivé."),
        },
    )
    def post(self, request, *args, **kwargs):
        # Appeler d'abord la methode parent pour valider le token
        response = super().post(request, *args, **kwargs)

        # Si le refresh a reussi, verifier que l'utilisateur est actif
        if response.status_code == 200:
            try:
                # Decoder le nouveau token d'acces pour obtenir l'user_id
                access_token = AccessToken(response.data['access'])
                user_id = access_token.get('user_id')

                # Verifier que l'utilisateur existe et est actif
                user = Role.objects.filter(id_role=user_id).first()
                if user is None:
                    raise InvalidToken({'detail': 'Utilisateur introuvable.'})
                if not user.active:
                    raise InvalidToken({'detail': 'Ce compte a ete desactive. Veuillez contacter un administrateur.'})

            except Role.DoesNotExist:
                raise InvalidToken({'detail': 'Utilisateur introuvable.'})

        return response


class PasswordResetRequestView(APIView):
    """
    Demande de réinitialisation de mot de passe (#329).

    POST /api/auth/password-reset/
    Body: {"email": "utilisateur@example.fr"}

    Envoie un email contenant un lien de réinitialisation si un compte actif
    correspond. La réponse est volontairement identique que le compte existe
    ou non, pour ne pas permettre l'énumération des adresses.
    """
    permission_classes = [ConnexionLocaleActive]
    throttle_classes = [AuthRateThrottle]

    @extend_schema(
        tags=['auth'],
        summary="Demander la réinitialisation du mot de passe",
        description=(
            "Envoie par email un lien de réinitialisation si un compte actif correspond "
            "à l'adresse. Public. La réponse est identique que le compte existe ou non "
            "(pas d'énumération des adresses, #329)."
        ),
        request=PasswordResetRequestSerializer,
        responses={
            200: OpenApiResponse(response=DetailSchema, description="Demande prise en compte (toujours, même sans compte associé)."),
            400: OpenApiResponse(description="Adresse email manquante ou invalide."),
            403: REPONSE_403_CONNEXION_EXTERNE,
            429: REPONSE_429,
        },
    )
    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']

        user = Role.objects.filter(email__iexact=email, active=True).first()
        if user and user.email:
            from apps.notifications.tasks import send_password_reset_email

            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            site_url = getattr(settings, 'SITE_URL', 'http://localhost:4200')
            reset_url = f"{site_url}/auth/reset-password?uid={uid}&token={token}"
            nom_complet = f"{user.prenom_role or ''} {user.nom_role or ''}".strip() or user.email
            try:
                send_password_reset_email.delay(user.email, reset_url, nom_complet)
            except Exception:
                # Ne jamais faire échouer la requête (ni révéler l'existence du
                # compte) si la file de tâches est indisponible.
                logger.exception("Échec de la mise en file de l'email de réinitialisation")

        return Response(
            {'detail': "Si un compte est associé à cette adresse, un email de "
                       "réinitialisation vient d'être envoyé."},
            status=status.HTTP_200_OK,
        )


class PasswordResetConfirmView(APIView):
    """
    Confirmation de réinitialisation de mot de passe (#329).

    POST /api/auth/password-reset/confirm/
    Body: {"uid": "...", "token": "...", "new_password": "..."}

    Valide le jeton (lié au hash du mot de passe courant, donc à usage unique)
    et applique le nouveau mot de passe.
    """
    permission_classes = [ConnexionLocaleActive]
    throttle_classes = [AuthRateThrottle]

    @extend_schema(
        tags=['auth'],
        summary="Appliquer un nouveau mot de passe",
        description=(
            "Valide le couple `uid` / `token` reçu dans le lien envoyé par email "
            "(jeton à usage unique) et enregistre le nouveau mot de passe. Public (#329)."
        ),
        request=PasswordResetConfirmSerializer,
        responses={
            200: OpenApiResponse(response=DetailSchema, description="Mot de passe réinitialisé."),
            400: OpenApiResponse(description="Lien invalide ou expiré, compte désactivé, ou mot de passe refusé par les validateurs."),
            403: REPONSE_403_CONNEXION_EXTERNE,
            429: REPONSE_429,
        },
    )
    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        uid = serializer.validated_data['uid']
        token = serializer.validated_data['token']
        new_password = serializer.validated_data['new_password']

        user = None
        try:
            pk = force_str(urlsafe_base64_decode(uid))
            user = Role.objects.get(pk=pk)
        except (TypeError, ValueError, OverflowError, Role.DoesNotExist):
            user = None

        if user is None or not default_token_generator.check_token(user, token):
            return Response(
                {'detail': "Le lien de réinitialisation est invalide ou a expiré. "
                           "Veuillez refaire une demande."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not user.active:
            return Response(
                {'detail': "Ce compte est désactivé."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.set_password(new_password)
        user.save(update_fields=['password'])
        logger.info(f"Password reset completed for user {user.pk}")

        return Response(
            {'detail': "Votre mot de passe a été réinitialisé. Vous pouvez "
                       "maintenant vous connecter."},
            status=status.HTTP_200_OK,
        )


@extend_schema(
    tags=['auth'],
    summary="Déconnexion",
    description=(
        "Révoque le jeton de rafraîchissement transmis (liste noire). Le jeton d'accès "
        "courant reste utilisable jusqu'à son expiration : le client doit l'oublier."
    ),
    request=inline_serializer(
        name='Deconnexion',
        fields={'refresh': serializers.CharField(required=False, help_text="Jeton de rafraîchissement à révoquer")},
    ),
    responses={
        200: inline_serializer(name='DeconnexionOk', fields={'message': serializers.CharField()}),
        400: OpenApiResponse(
            response=inline_serializer(name='DeconnexionErreur', fields={'error': serializers.CharField()}),
            description="Jeton de rafraîchissement invalide.",
        ),
        401: REPONSE_401,
    },
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_view(request):
    """
    Vue pour deconnecter un utilisateur en blacklistant son refresh token.
    """
    try:
        refresh_token = request.data.get('refresh')
        if refresh_token:
            token = RefreshToken(refresh_token)
            token.blacklist()

        return Response(
            {'message': 'Deconnexion reussie'},
            status=status.HTTP_200_OK
        )
    except TokenError:
        return Response(
            {'error': 'Token invalide'},
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception:
        return Response(
            {'error': 'Erreur lors de la deconnexion'},
            status=status.HTTP_400_BAD_REQUEST
        )


@extend_schema(
    tags=['auth'],
    summary="Profil de l'utilisateur connecté",
    description="Renvoie le compte associé au jeton d'accès (rôle, organisme, statut référent).",
    responses={200: UserInfoSerializer, 401: REPONSE_401},
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_info_view(request):
    """
    Vue pour obtenir les informations de l'utilisateur connecte.
    """
    serializer = UserInfoSerializer(request.user)
    return Response(serializer.data)


@extend_schema(
    tags=['auth'],
    summary="Accepter les conditions générales d'utilisation",
    description=(
        "#746 — Enregistre l'acceptation, par l'utilisateur connecté, de la version en vigueur des CGU "
        "de l'instance. `version` est la `cgu_version` lue sur `/api/settings/` : si le texte a changé "
        "depuis, la requête est refusée (409) et la nouvelle version doit être relue. Refusé pendant une "
        "impersonation : l'administrateur ne peut pas accepter à la place de l'utilisateur."
    ),
    request=inline_serializer(name='AcceptationCgu', fields={'version': serializers.DateTimeField()}),
    responses={
        200: inline_serializer(name='CguAcceptees', fields={
            'cgu_a_accepter': serializers.BooleanField(),
            'cgu_acceptees_le': serializers.DateTimeField(),
        }),
        400: OpenApiResponse(response=DetailSchema, description="Version absente ou illisible."),
        401: REPONSE_401,
        403: REPONSE_403,
        409: OpenApiResponse(response=DetailSchema, description="Les CGU ont changé : relire la nouvelle version."),
    },
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def accepter_cgu_view(request):
    """#746 — POST /api/auth/cgu/accepter/ : l'utilisateur accepte les CGU en vigueur."""
    from apps.core.models import SiteConfiguration

    if request.auth is not None and request.auth.get('is_impersonating'):
        return Response(
            {'detail': _("Seul l'utilisateur peut accepter les conditions générales d'utilisation.")},
            status=status.HTTP_403_FORBIDDEN,
        )
    try:
        version = serializers.DateTimeField().to_internal_value(request.data.get('version') or '')
    except serializers.ValidationError:
        return Response({'detail': _("Version des CGU manquante ou illisible.")},
                        status=status.HTTP_400_BAD_REQUEST)
    if version != SiteConfiguration.get_instance().cgu_version:
        return Response(
            {'detail': _("Les conditions générales d'utilisation ont été modifiées : relisez la nouvelle version.")},
            status=status.HTTP_409_CONFLICT,
        )
    user = request.user
    user.cgu_acceptees_le = timezone.now()
    user.save(update_fields=['cgu_acceptees_le'])
    return Response({'cgu_a_accepter': False, 'cgu_acceptees_le': user.cgu_acceptees_le})


@extend_schema(
    tags=['auth'],
    summary="État de l'API d'authentification",
    description="Sonde publique, sans authentification : répond `ok` si l'application est démarrée.",
    auth=[],
    responses={
        200: inline_serializer(
            name='SanteAuth',
            fields={'status': serializers.CharField(), 'message': serializers.CharField()},
        ),
    },
)
@api_view(['GET'])
@permission_classes([])  # Endpoint public
def health_check_view(request):
    """
    Vue de verification de l'etat de l'API d'authentification.
    """
    return Response({
        'status': 'ok',
        'message': 'API d\'authentification fonctionnelle'
    })


def get_client_ip(request):
    """Recupere l'adresse IP du client."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


@extend_schema(
    tags=['auth'],
    summary="Démarrer une impersonation (super admin)",
    description=(
        "Délivre des jetons JWT au nom de l'utilisateur cible, porteurs des claims "
        "`is_impersonating`, `impersonator_id`, `impersonator_email` et "
        "`impersonation_log_id`. Réservé aux super administrateurs ; impossible sur "
        "soi-même ou sur un autre super administrateur. Chaque session est journalisée."
    ),
    parameters=[OpenApiParameter('user_id', OpenApiTypes.INT, OpenApiParameter.PATH, description="Identifiant (id_role) de l'utilisateur à impersonner")],
    request=inline_serializer(
        name='DemarrerImpersonation',
        fields={'reason': serializers.CharField(required=False, allow_blank=True, help_text="Motif, consigné dans le journal")},
    ),
    responses={
        200: inline_serializer(
            name='ImpersonationDemarree',
            fields={
                'refresh': serializers.CharField(),
                'access': serializers.CharField(),
                'user': ProfilConnexionSchema(help_text="Utilisateur impersonné"),
                'impersonation': inline_serializer(
                    name='ContexteImpersonation',
                    fields={
                        'isImpersonating': serializers.BooleanField(),
                        'impersonator': inline_serializer(
                            name='Impersonateur',
                            fields={
                                'id': serializers.IntegerField(),
                                'email': serializers.EmailField(),
                                'nom_role': serializers.CharField(allow_null=True),
                                'prenom_role': serializers.CharField(allow_null=True),
                            },
                        ),
                        'logId': serializers.IntegerField(),
                        'startedAt': serializers.DateTimeField(),
                    },
                ),
            },
        ),
        400: OpenApiResponse(response=DetailSchema, description="Tentative d'auto-impersonation."),
        401: REPONSE_401,
        403: OpenApiResponse(response=DetailSchema, description="Appelant non super admin, ou cible super admin."),
        404: OpenApiResponse(description="Utilisateur cible introuvable."),
    },
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def start_impersonation_view(request, user_id):
    """
    Demarre une session d'impersonation.
    Seuls les super_admin peuvent utiliser cette fonctionnalite.

    POST /api/auth/impersonate/<user_id>/
    Body (optionnel): {"reason": "Motif de l'impersonation"}

    Retourne les tokens JWT pour l'utilisateur cible avec des claims supplementaires
    indiquant qu'il s'agit d'une session d'impersonation.
    """
    # Verifier que l'utilisateur est super_admin
    if not request.user.is_super_admin():
        return Response(
            {'detail': "Seuls les super administrateurs peuvent utiliser cette fonctionnalite."},
            status=status.HTTP_403_FORBIDDEN
        )

    # Recuperer l'utilisateur cible
    target_user = get_object_or_404(Role, id_role=user_id)

    # Empecher l'auto-impersonation
    if target_user.id_role == request.user.id_role:
        return Response(
            {'detail': "Vous ne pouvez pas vous impersonner vous-meme."},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Empecher l'impersonation d'un autre super_admin
    if target_user.is_super_admin():
        return Response(
            {'detail': "Vous ne pouvez pas impersonner un autre super administrateur."},
            status=status.HTTP_403_FORBIDDEN
        )

    # Creer le log d'impersonation
    log = ImpersonationLog.objects.create(
        impersonator=request.user,
        impersonated_user=target_user,
        ip_address=get_client_ip(request),
        user_agent=request.META.get('HTTP_USER_AGENT', ''),
        reason=request.data.get('reason', '')
    )

    # Generer un token JWT pour l'utilisateur cible
    refresh = RefreshToken.for_user(target_user)

    # Ajouter des claims personnalises pour l'impersonation
    refresh['is_impersonating'] = True
    refresh['impersonator_id'] = request.user.id_role
    refresh['impersonator_email'] = request.user.email
    refresh['impersonation_log_id'] = log.id

    # Ajouter les memes claims au token d'acces
    access_token = refresh.access_token
    access_token['is_impersonating'] = True
    access_token['impersonator_id'] = request.user.id_role
    access_token['impersonator_email'] = request.user.email
    access_token['impersonation_log_id'] = log.id

    return Response({
        'refresh': str(refresh),
        'access': str(access_token),
        'user': {
            'id': target_user.id_role,
            'email': target_user.email,
            'nom_role': target_user.nom_role,
            'prenom_role': target_user.prenom_role,
            'identifiant': target_user.identifiant,
            'niveau_role': target_user.role_level,
            'is_staff': target_user.is_staff,
            'is_active': target_user.active,
            'is_referent': target_user.is_referent(),
            'organisme': {
                'id_organisme': target_user.id_organisme.id_organisme,
                'nom_organisme': target_user.id_organisme.nom_organisme,
            } if target_user.id_organisme else None
        },
        'impersonation': {
            'isImpersonating': True,
            'impersonator': {
                'id': request.user.id_role,
                'email': request.user.email,
                'nom_role': request.user.nom_role,
                'prenom_role': request.user.prenom_role,
            },
            'logId': log.id,
            'startedAt': log.started_at.isoformat()
        }
    }, status=status.HTTP_200_OK)


@extend_schema(
    tags=['auth'],
    summary="Terminer une impersonation",
    description=(
        "À appeler avec le jeton d'accès **de la session d'impersonation** : les claims "
        "du jeton identifient l'administrateur d'origine, dont de nouveaux jetons sont "
        "renvoyés, et le journal est clôturé. Aucun corps de requête n'est lu."
    ),
    request=None,
    responses={
        200: inline_serializer(
            name='ImpersonationTerminee',
            fields={
                'refresh': serializers.CharField(),
                'access': serializers.CharField(),
                'user': ProfilConnexionSchema(help_text="Administrateur d'origine"),
                'message': serializers.CharField(),
            },
        ),
        400: OpenApiResponse(response=DetailSchema, description="Le jeton n'est pas celui d'une session d'impersonation."),
        401: OpenApiResponse(response=DetailSchema, description="Jeton absent, invalide ou expiré."),
        404: OpenApiResponse(response=DetailSchema, description="Administrateur d'origine introuvable."),
    },
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def stop_impersonation_view(request):
    """
    Arrete une session d'impersonation et retourne les tokens du super_admin original.

    POST /api/auth/stop-impersonation/
    Body: {"log_id": <id_du_log>}

    Note: Cette vue est appelee avec le token de l'utilisateur impersonne,
    mais elle verifie le claim impersonator_id pour retrouver l'admin original.
    """
    import jwt
    from django.conf import settings

    # Recuperer le token d'acces actuel
    auth_header = request.META.get('HTTP_AUTHORIZATION', '')
    if not auth_header.startswith('Bearer '):
        return Response(
            {'detail': "Token d'authentification manquant."},
            status=status.HTTP_401_UNAUTHORIZED
        )

    token = auth_header.split(' ')[1]

    try:
        # Decoder le token pour recuperer les claims d'impersonation
        decoded = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=['HS256']
        )
    except jwt.ExpiredSignatureError:
        return Response(
            {'detail': "Le token a expire."},
            status=status.HTTP_401_UNAUTHORIZED
        )
    except jwt.InvalidTokenError:
        return Response(
            {'detail': "Token invalide."},
            status=status.HTTP_401_UNAUTHORIZED
        )

    # Verifier que c'est bien une session d'impersonation
    if not decoded.get('is_impersonating'):
        return Response(
            {'detail': "Vous n'etes pas en mode impersonation."},
            status=status.HTTP_400_BAD_REQUEST
        )

    impersonator_id = decoded.get('impersonator_id')
    log_id = decoded.get('impersonation_log_id')

    # Recuperer l'admin original
    try:
        original_admin = Role.objects.get(id_role=impersonator_id)
    except Role.DoesNotExist:
        return Response(
            {'detail': "Administrateur original introuvable."},
            status=status.HTTP_404_NOT_FOUND
        )

    # Mettre a jour le log d'impersonation
    if log_id:
        try:
            log = ImpersonationLog.objects.get(id=log_id)
            log.ended_at = timezone.now()
            log.save()
        except ImpersonationLog.DoesNotExist:
            pass  # Le log n'existe pas, on continue quand meme

    # Generer un nouveau token pour l'admin original
    refresh = RefreshToken.for_user(original_admin)

    return Response({
        'refresh': str(refresh),
        'access': str(refresh.access_token),
        'user': {
            'id': original_admin.id_role,
            'email': original_admin.email,
            'nom_role': original_admin.nom_role,
            'prenom_role': original_admin.prenom_role,
            'identifiant': original_admin.identifiant,
            'niveau_role': original_admin.role_level,
            'is_staff': original_admin.is_staff,
            'is_active': original_admin.active,
            'is_referent': original_admin.is_referent(),
            'cgu_a_accepter': original_admin.doit_accepter_cgu(),
            'organisme': {
                'id_organisme': original_admin.id_organisme.id_organisme,
                'nom_organisme': original_admin.id_organisme.nom_organisme,
            } if original_admin.id_organisme else None
        },
        'message': "Session d'impersonation terminee."
    }, status=status.HTTP_200_OK)



# Composant partagé par `impersonator` et `impersonated_user` : un même nom
# d'inline_serializer doit désigner une seule identité, sinon drf-spectacular
# signale deux composants homonymes.
PERSONNE_IMPERSONATION_SCHEMA = inline_serializer(
    name='PersonneImpersonation',
    fields={
        'id': serializers.IntegerField(),
        'email': serializers.EmailField(),
        'nom_complet': serializers.CharField(),
    },
)

@extend_schema(
    tags=['auth'],
    summary="Journal des impersonations (super admin)",
    description="Les 100 dernières sessions d'impersonation, de la plus récente à la plus ancienne, avec filtres optionnels.",
    parameters=[
        OpenApiParameter('impersonator_id', OpenApiTypes.INT, OpenApiParameter.QUERY, description="Ne garder que les sessions ouvertes par cet administrateur"),
        OpenApiParameter('impersonated_user_id', OpenApiTypes.INT, OpenApiParameter.QUERY, description="Ne garder que les sessions visant cet utilisateur"),
        OpenApiParameter('active_only', OpenApiTypes.BOOL, OpenApiParameter.QUERY, description="`true` : sessions encore ouvertes seulement"),
    ],
    responses={
        200: inline_serializer(
            name='JournalImpersonations',
            fields={
                'count': serializers.IntegerField(),
                'results': serializers.ListField(child=inline_serializer(
                    name='SessionImpersonation',
                    fields={
                        'id': serializers.IntegerField(),
                        'impersonator': PERSONNE_IMPERSONATION_SCHEMA,
                        'impersonated_user': PERSONNE_IMPERSONATION_SCHEMA,
                        'started_at': serializers.DateTimeField(),
                        'ended_at': serializers.DateTimeField(allow_null=True),
                        'is_active': serializers.BooleanField(),
                        'duration_seconds': serializers.FloatField(allow_null=True, help_text="Durée en secondes (null si session encore ouverte)"),
                        'ip_address': serializers.CharField(allow_null=True),
                        'reason': serializers.CharField(allow_blank=True),
                    },
                )),
            },
        ),
        401: REPONSE_401,
        403: REPONSE_403,
    },
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def impersonation_logs_view(request):
    """
    Liste les logs d'impersonation (pour les super_admin uniquement).

    GET /api/auth/impersonation-logs/
    Query params:
        - impersonator_id: Filtrer par admin
        - impersonated_user_id: Filtrer par utilisateur cible
        - active_only: Ne montrer que les sessions actives
    """
    if not request.user.is_super_admin():
        return Response(
            {'detail': "Seuls les super administrateurs peuvent consulter ces logs."},
            status=status.HTTP_403_FORBIDDEN
        )

    queryset = ImpersonationLog.objects.select_related(
        'impersonator', 'impersonated_user'
    ).all()

    # Filtres optionnels
    impersonator_id = request.query_params.get('impersonator_id')
    if impersonator_id:
        queryset = queryset.filter(impersonator_id=impersonator_id)

    impersonated_user_id = request.query_params.get('impersonated_user_id')
    if impersonated_user_id:
        queryset = queryset.filter(impersonated_user_id=impersonated_user_id)

    active_only = request.query_params.get('active_only', '').lower() == 'true'
    if active_only:
        queryset = queryset.filter(ended_at__isnull=True)

    # Limiter aux 100 derniers logs
    logs = queryset[:100]

    return Response({
        'count': len(logs),
        'results': [
            {
                'id': log.id,
                'impersonator': {
                    'id': log.impersonator.id_role,
                    'email': log.impersonator.email,
                    'nom_complet': f"{log.impersonator.prenom_role or ''} {log.impersonator.nom_role or ''}".strip()
                },
                'impersonated_user': {
                    'id': log.impersonated_user.id_role,
                    'email': log.impersonated_user.email,
                    'nom_complet': f"{log.impersonated_user.prenom_role or ''} {log.impersonated_user.nom_role or ''}".strip()
                },
                'started_at': log.started_at.isoformat(),
                'ended_at': log.ended_at.isoformat() if log.ended_at else None,
                'is_active': log.is_active,
                'duration_seconds': log.duration,
                'ip_address': log.ip_address,
                'reason': log.reason
            }
            for log in logs
        ]
    })


@extend_schema(
    tags=['auth'],
    summary="Statistiques publiques de l'instance",
    description="Compteurs affichés sur la page d'accueil, sans authentification : sites actifs, plans validés, organismes.",
    auth=[],
    responses={
        200: inline_serializer(
            name='StatistiquesPubliques',
            fields={
                'sites_count': serializers.IntegerField(),
                'plans_count': serializers.IntegerField(),
                'organismes_count': serializers.IntegerField(),
            },
        ),
    },
)
@api_view(['GET'])
@permission_classes([AllowAny])
def public_stats_view(request):
    """
    Vue publique retournant des statistiques generales sur la plateforme.
    Ces donnees sont accessibles sans authentification.

    GET /api/auth/stats/

    Retourne:
        - sites_count: Nombre de sites actifs
        - plans_count: Nombre de plans de gestion (hors brouillons)
        - organismes_count: Nombre d'organismes
    """
    # Compter les sites actifs
    sites_count = Site.objects.filter(active=True).count()

    # Compter les plans de gestion (valides uniquement, pas les brouillons)
    plans_count = PlanGestion.objects.filter(statut='valide').count()

    # Compter les organismes
    organismes_count = BibOrganismes.objects.count()

    return Response({
        'sites_count': sites_count,
        'plans_count': plans_count,
        'organismes_count': organismes_count
    })
