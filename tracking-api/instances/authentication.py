"""
Authentification par token d'instance
"""
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from .models import Instance


class InstanceTokenAuthentication(BaseAuthentication):
    """Authentification par token d'instance dans le header X-Instance-Token"""
    def authenticate(self, request):
        token = request.META.get('HTTP_X_INSTANCE_TOKEN')
        if not token:
            return None

        try:
            instance = Instance.objects.get(token=token, is_active=True)
            return (instance, None)  # (user, auth)
        except Instance.DoesNotExist:
            raise AuthenticationFailed('Token invalide ou instance inactive')
