"""
Development settings for Outil Plan de Gestion project.
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
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

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