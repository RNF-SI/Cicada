"""
Development settings for CICADA project.
"""

from .base import *

# Debug mode
DEBUG = True

# Allowed hosts for development
ALLOWED_HOSTS = ['localhost', '127.0.0.1', 'web', 'frontend', '0.0.0.0', 'testserver']

# CORS settings for development
CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True

# Email backend for development
# Par défaut: utilise Mailpit si configuré, sinon console
import os
EMAIL_BACKEND = os.environ.get('EMAIL_BACKEND', 'django.core.mail.backends.console.EmailBackend')
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'mailpit')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', 1025))
EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', 'false').lower() == 'true'
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')

# =============================================================================
# DEVELOPMENT LOGGING CONFIGURATION
# =============================================================================
# Surcharge la configuration de base pour le developpement:
# - Format lisible (pas JSON)
# - Niveau DEBUG
# - Console uniquement (pas de fichiers)
# - Option pour activer les logs SQL

from copy import deepcopy

LOGGING = deepcopy(LOGGING)

# En dev, utiliser le format lisible sur la console
LOGGING['handlers']['console']['formatter'] = 'verbose'

# Niveau DEBUG pour le developpement
LOGGING['loggers']['root']['level'] = 'DEBUG'
LOGGING['loggers']['apps']['level'] = 'DEBUG'
LOGGING['loggers']['django']['level'] = 'DEBUG'
LOGGING['loggers']['django.request']['level'] = 'DEBUG'
LOGGING['loggers']['http']['level'] = 'DEBUG'

# Activer les logs SQL si LOG_SQL=true
import os
if os.environ.get('LOG_SQL', 'false').lower() == 'true':
    LOGGING['loggers']['django.db.backends']['level'] = 'DEBUG'

# Extended JWT token lifetime for development
# Access token: 24 hours (instead of 60 min) - less frequent re-auth during dev
# Refresh token: 30 days (instead of 7 days) - longer dev sessions
from datetime import timedelta
SIMPLE_JWT = {
    **SIMPLE_JWT,
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=24),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=30),
}

# =============================================================================
# CELERY CONFIGURATION FOR DEVELOPMENT/TESTS
# =============================================================================
# En développement, exécuter les tâches Celery de manière synchrone
# Cela permet de tester les emails sans avoir besoin du worker Celery
# Note: En production, ces valeurs doivent être False pour utiliser le worker
CELERY_TASK_ALWAYS_EAGER = os.environ.get('CELERY_TASK_ALWAYS_EAGER', 'true').lower() == 'true'
CELERY_TASK_EAGER_PROPAGATES = True