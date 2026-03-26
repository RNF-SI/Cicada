"""
Rate limiting pour les endpoints d'authentification.
Protège contre les attaques par force brute sur login et register.
"""
from rest_framework.throttling import AnonRateThrottle


class AuthRateThrottle(AnonRateThrottle):
    """
    Limite les tentatives de connexion et d'inscription.
    Rate configurable via DEFAULT_THROTTLE_RATES['auth'] dans settings.
    Par défaut : 5 requêtes par minute par IP.
    """
    scope = 'auth'
