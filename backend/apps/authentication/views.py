"""
Vues pour l'authentification JWT.
"""
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken

from .serializers import CustomTokenObtainPairSerializer, UserInfoSerializer


class CustomTokenObtainPairView(TokenObtainPairView):
    """
    Vue personnalisée pour obtenir les tokens JWT.
    """
    serializer_class = CustomTokenObtainPairSerializer


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_view(request):
    """
    Vue pour déconnecter un utilisateur en blacklistant son refresh token.
    """
    try:
        refresh_token = request.data.get('refresh')
        if refresh_token:
            token = RefreshToken(refresh_token)
            token.blacklist()
            
        return Response(
            {'message': 'Déconnexion réussie'}, 
            status=status.HTTP_200_OK
        )
    except TokenError as e:
        return Response(
            {'error': 'Token invalide'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        return Response(
            {'error': 'Erreur lors de la déconnexion'}, 
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_info_view(request):
    """
    Vue pour obtenir les informations de l'utilisateur connecté.
    """
    serializer = UserInfoSerializer(request.user)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([])  # Endpoint public
def health_check_view(request):
    """
    Vue de vérification de l'état de l'API d'authentification.
    """
    return Response({
        'status': 'ok',
        'message': 'API d\'authentification fonctionnelle'
    })