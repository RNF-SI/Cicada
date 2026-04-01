"""
Rate limiting pour les endpoints d'authentification.
Protège contre les attaques par force brute sur login et register.

Inclut des classes résilientes qui "fail open" en cas d'erreur Redis,
pour éviter que le throttle ne bloque toutes les requêtes quand le cache
est temporairement indisponible.
"""
import logging

from rest_framework.throttling import AnonRateThrottle, UserRateThrottle

logger = logging.getLogger('apps')


class ResilientUserRateThrottle(UserRateThrottle):
    """
    UserRateThrottle qui laisse passer les requêtes si Redis est indisponible.
    Évite qu'une erreur Redis transitoire ne provoque des 500 sur toute l'API.
    """

    def allow_request(self, request, view):
        try:
            return super().allow_request(request, view)
        except Exception:
            logger.warning(
                'Redis indisponible pour le throttle user — requête autorisée par défaut'
            )
            return True


class ResilientAnonRateThrottle(AnonRateThrottle):
    """
    AnonRateThrottle qui laisse passer les requêtes si Redis est indisponible.
    """

    def allow_request(self, request, view):
        try:
            return super().allow_request(request, view)
        except Exception:
            logger.warning(
                'Redis indisponible pour le throttle anon — requête autorisée par défaut'
            )
            return True


class AuthRateThrottle(ResilientAnonRateThrottle):
    """
    Limite les tentatives de connexion et d'inscription.
    Rate configurable via DEFAULT_THROTTLE_RATES['auth'] dans settings.
    Par défaut : 5 requêtes par minute par IP.
    """
    scope = 'auth'
