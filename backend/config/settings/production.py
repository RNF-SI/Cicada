"""
Production settings for CICADA project.
"""

from .base import *
import os

# Vérifier que SECRET_KEY a été définie explicitement (pas la valeur par défaut insécure)
if SECRET_KEY == 'django-insecure-change-me':
    raise ValueError(
        "SECRET_KEY non configurée ! "
        "Définissez la variable d'environnement SECRET_KEY avec une clé secrète unique. "
        "Générez-en une avec : python -c \"import secrets; print(secrets.token_urlsafe(50))\""
    )

# Security settings
DEBUG = False
ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '').split(',')

# Static files - using WhiteNoise or external CDN
STATIC_ROOT = '/app/static/'
MEDIA_ROOT = '/app/media/'

# Security middleware
# Desactiver SSL_REDIRECT si pas de certificat SSL configure (ENABLE_SSL=false dans .env)
_enable_ssl = os.environ.get('ENABLE_SSL', 'false').lower() == 'true'
SECURE_SSL_REDIRECT = _enable_ssl
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
SECURE_HSTS_SECONDS = 31536000 if _enable_ssl else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = _enable_ssl
SECURE_HSTS_PRELOAD = _enable_ssl
SECURE_REDIRECT_EXEMPT = [r'^api/health/$']

# Session security
SESSION_COOKIE_SECURE = _enable_ssl
CSRF_COOKIE_SECURE = _enable_ssl
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True

# =============================================================================
# PRODUCTION LOGGING CONFIGURATION
# =============================================================================
# Surcharge la configuration de base pour la production:
# - Logs JSON structures vers fichiers avec rotation
# - Console en JSON pour Docker/orchestrateurs
# - Niveau WARNING minimum
# - Fichiers separes pour erreurs et audit

from copy import deepcopy

# Copier la config de base et la modifier pour la production
LOGGING = deepcopy(LOGGING)

# En production, utiliser JSON sur la console aussi
LOGGING['handlers']['console']['formatter'] = 'json'

# Ajouter les fichiers de logs en production
LOGGING['loggers']['root']['handlers'] = ['console_json', 'file', 'error_file']
LOGGING['loggers']['root']['level'] = 'WARNING'

LOGGING['loggers']['apps']['handlers'] = ['console_json', 'file', 'error_file']
LOGGING['loggers']['apps']['level'] = 'INFO'

LOGGING['loggers']['django']['handlers'] = ['console_json', 'file', 'error_file']
LOGGING['loggers']['django']['level'] = 'WARNING'

LOGGING['loggers']['django.request']['handlers'] = ['console_json', 'file', 'error_file']
LOGGING['loggers']['django.request']['level'] = 'WARNING'

LOGGING['loggers']['django.server']['handlers'] = ['console_json', 'file', 'error_file']

LOGGING['loggers']['celery']['handlers'] = ['console_json', 'file', 'error_file']
LOGGING['loggers']['celery']['level'] = 'INFO'

LOGGING['loggers']['audit']['handlers'] = ['console_json', 'audit_file']
LOGGING['loggers']['audit']['level'] = 'INFO'

LOGGING['loggers']['http']['handlers'] = ['console_json', 'file']
LOGGING['loggers']['http']['level'] = 'INFO'

# CORS settings for production
CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS = [origin for origin in os.environ.get('CORS_ALLOWED_ORIGINS', '').split(',') if origin]

# Cache configuration
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': os.environ.get('REDIS_URL', 'redis://redis:6379/0'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}

# Email configuration (à configurer selon l'infrastructure)
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.environ.get('EMAIL_HOST', '')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', 587))
EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', 'true').lower() == 'true'
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'noreply@outil-plan-gestion.fr')

# URL du frontend (pour les liens dans les emails)
SITE_URL = os.environ.get('SITE_URL', 'http://localhost:4200')