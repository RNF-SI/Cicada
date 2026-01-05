"""
Vues pour l'authentification JWT.
"""
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenRefreshView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError

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
