"""
Vues pour l'authentification JWT.
"""
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenRefreshView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError

from apps.users.models import Role
from .models import ImpersonationLog
from .serializers import CustomTokenObtainPairSerializer, UserInfoSerializer


class CustomTokenObtainPairView(APIView):
    """
    Vue personnalisee pour obtenir les tokens JWT.
    Accepte soit un email soit un identifiant (pseudo) pour la connexion.

    POST /api/auth/login/
    Body: {"username": "email_ou_identifiant", "password": "mot_de_passe"}
    """
    permission_classes = [AllowAny]

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


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_info_view(request):
    """
    Vue pour obtenir les informations de l'utilisateur connecte.
    """
    serializer = UserInfoSerializer(request.user)
    return Response(serializer.data)


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
            'organisme': {
                'id': target_user.id_organisme.id_organisme,
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
            'organisme': {
                'id': original_admin.id_organisme.id_organisme,
                'nom_organisme': original_admin.id_organisme.nom_organisme,
            } if original_admin.id_organisme else None
        },
        'message': "Session d'impersonation terminee."
    }, status=status.HTTP_200_OK)


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
