"""
Base settings for CICADA project.
"""

import os
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-change-me')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get('DEBUG', 'False').lower() == 'true'

ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', 'localhost').split(',')

# Authentication provider: 'local' (default) or 'keycloak'
# When 'keycloak', RGPD account management is handled externally
AUTH_PROVIDER = os.environ.get('AUTH_PROVIDER', 'local')

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.gis',
    'rest_framework',
    'rest_framework_simplejwt',
    # 'rest_framework_gis',  # Sera réactivé après build container
    'django_filters',
    'corsheaders',
    # Apps locales
    'apps.core',
    'apps.users',
    'apps.authentication',
    'apps.plans',
    'apps.notifications',
    'apps.taxonomy',
    'apps.habitats',
    'apps.geology',
    'apps.campanule',
    'apps.system',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    # Middleware de logging (doit etre avant les autres middleware custom)
    'apps.core.middleware.logging.RequestLoggingMiddleware',
    # Middleware personnalise pour les permissions
    'apps.users.middleware.SecurityHeadersMiddleware',
    'apps.users.middleware.PermissionMiddleware',
    'apps.users.middleware.AuditMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# Database
# Multi-schema architecture: utilisateurs, referentiels, ref_nomenclatures, general, fichiers, gn_commons
DATABASES = {
    'default': {
        'ENGINE': 'django.contrib.gis.db.backends.postgis',
        'NAME': os.environ.get('POSTGRES_DB', 'cicada'),
        'USER': os.environ.get('POSTGRES_USER', 'cicada_user'),
        'PASSWORD': os.environ.get('POSTGRES_PASSWORD', 'cicada_password'),
        'HOST': os.environ.get('POSTGRES_HOST', 'db'),
        'PORT': os.environ.get('POSTGRES_PORT', '5432'),
        'OPTIONS': {
            'options': '-c search_path=utilisateurs,referentiels,ref_nomenclatures,ref_geo,general,fichiers,ccd_commons,ccd_notifications,taxonomie,ref_habitats,ref_inpg,ref_campanule,public'
        },
    }
}

# Internationalization
from django.utils.translation import gettext_lazy as _

LANGUAGE_CODE = 'fr-fr'
TIME_ZONE = 'Europe/Paris'
USE_I18N = True
USE_L10N = True
USE_TZ = True

# Available languages
LANGUAGES = [
    ('fr', _('Francais')),
    ('en', _('English')),
]

# Path to locale files
LOCALE_PATHS = [
    BASE_DIR / 'locale',
]

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'static')

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# User model personnalisé
AUTH_USER_MODEL = 'users.Role'

# REST Framework
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
}

# JWT Configuration
from datetime import timedelta

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': True,
    
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'VERIFYING_KEY': None,
    'AUDIENCE': None,
    'ISSUER': None,
    
    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',
    'USER_ID_FIELD': 'id_role',
    'USER_ID_CLAIM': 'user_id',
    'USER_AUTHENTICATION_RULE': 'rest_framework_simplejwt.authentication.default_user_authentication_rule',
    
    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
    'TOKEN_TYPE_CLAIM': 'token_type',
}

# Django REST Framework settings
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'apps.users.pagination.UsersPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
    ],
    'EXCEPTION_HANDLER': 'apps.core.exception_handler.exception_handler',
    'TEST_REQUEST_DEFAULT_FORMAT': 'json',
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/hour',
        'user': '1000/hour',
        'auth': '5/minute',
    },
}

# CORS settings
CORS_ALLOW_ALL_ORIGINS = DEBUG
CORS_ALLOWED_ORIGINS = os.environ.get('CORS_ALLOWED_ORIGINS', '').split(',') if os.environ.get('CORS_ALLOWED_ORIGINS') else []

# Celery Configuration
CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', 'redis://redis:6379/0')
CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', 'redis://redis:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60  # 30 minutes

# Celery Beat - Taches periodiques
from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    # Nettoyage des anciens logs d'erreur - tous les jours a 3h du matin
    'cleanup-old-error-logs': {
        'task': 'core.cleanup_old_error_logs',
        'schedule': crontab(hour=3, minute=0),
        'kwargs': {'days': 90, 'acknowledged_days': 30},
    },
    # Audit hebdomadaire des organismes sans admin - tous les lundis a 8h
    # Note: La detection en temps reel est faite par les signaux Django (users/signals.py)
    # Cette tache sert de filet de securite pour detecter les cas manques
    'check-organismes-no-admin': {
        'task': 'apps.notifications.tasks.check_organismes_without_admin',
        'schedule': crontab(hour=8, minute=0, day_of_week=1),  # Lundi
    },
    # Audit hebdomadaire des sites orphelins - tous les lundis a 8h30
    # Note: La detection en temps reel est faite par les signaux Django (users/signals.py)
    # Cette tache sert de filet de securite pour detecter les cas manques
    'check-orphaned-sites': {
        'task': 'apps.notifications.tasks.check_orphaned_sites',
        'schedule': crontab(hour=8, minute=30, day_of_week=1),  # Lundi
    },
    # Nettoyage des anciennes notifications - tous les jours a 4h
    'cleanup-old-notifications': {
        'task': 'apps.notifications.tasks.cleanup_old_notifications',
        'schedule': crontab(hour=4, minute=0),
    },
    # Expiration des inscriptions en attente - tous les jours a 5h
    'cleanup-expired-pending-users': {
        'task': 'apps.notifications.tasks.cleanup_expired_pending_users',
        'schedule': crontab(hour=5, minute=0),
    },
    # Note: Le traitement des demandes RGPD est maintenant manuel via l'interface admin
    # Les super_admins decident quand desactiver ou anonymiser les comptes
}

# Email backend (sera configure differemment en dev/prod)
EMAIL_BACKEND = os.environ.get('EMAIL_BACKEND', 'django.core.mail.backends.console.EmailBackend')
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'noreply@outil-plan-gestion.fr')

# =============================================================================
# LOGGING CONFIGURATION
# =============================================================================

# Log directory and level from environment
LOG_DIR = os.environ.get('LOG_DIR', os.path.join(BASE_DIR, 'logs'))
LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
LOG_SQL = os.environ.get('LOG_SQL', 'false').lower() == 'true'

# Ensure log directory exists
os.makedirs(LOG_DIR, exist_ok=True)

# Base logging configuration (overridden in development.py and production.py)
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        # Format lisible pour le developpement
        'verbose': {
            'format': '[{asctime}] {levelname} {name} {correlation_id} {message}',
            'style': '{',
            'datefmt': '%Y-%m-%d %H:%M:%S',
            'defaults': {'correlation_id': '-'},
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
        # Format JSON structure pour la production
        'json': {
            '()': 'pythonjsonlogger.jsonlogger.JsonFormatter',
            'format': '%(asctime)s %(levelname)s %(name)s %(message)s',
            'rename_fields': {
                'asctime': 'timestamp',
                'levelname': 'level',
                'name': 'logger',
            },
        },
    },
    'filters': {
        'correlation_id': {
            '()': 'apps.core.middleware.logging.CorrelationIdFilter',
        },
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse',
        },
        'require_debug_true': {
            '()': 'django.utils.log.RequireDebugTrue',
        },
    },
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
            'filters': ['correlation_id'],
        },
        'console_json': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'json',
            'filters': ['correlation_id'],
        },
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(LOG_DIR, 'django.log'),
            'maxBytes': 10 * 1024 * 1024,  # 10 MB
            'backupCount': 10,
            'formatter': 'json',
            'filters': ['correlation_id'],
        },
        'error_file': {
            'level': 'ERROR',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(LOG_DIR, 'error.log'),
            'maxBytes': 10 * 1024 * 1024,  # 10 MB
            'backupCount': 10,
            'formatter': 'json',
            'filters': ['correlation_id'],
        },
        'audit_file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(LOG_DIR, 'audit.log'),
            'maxBytes': 10 * 1024 * 1024,  # 10 MB
            'backupCount': 20,
            'formatter': 'json',
            'filters': ['correlation_id'],
        },
        # Handler pour stocker les erreurs en base de donnees
        'db_errors': {
            'level': 'ERROR',
            'class': 'apps.core.logging_handlers.DatabaseLogHandler',
        },
    },
    'loggers': {
        # Logger racine
        'root': {
            'handlers': ['console'],
            'level': LOG_LEVEL,
        },
        # Logger pour les applications
        'apps': {
            'handlers': ['console', 'db_errors'],
            'level': LOG_LEVEL,
            'propagate': False,
        },
        # Logger pour Django
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        # Logger pour les requetes Django (dev only)
        'django.request': {
            'handlers': ['console', 'db_errors'],
            'level': 'INFO',
            'propagate': False,
        },
        # Logger pour les erreurs de serveur
        'django.server': {
            'handlers': ['console'],
            'level': 'WARNING',
            'propagate': False,
        },
        # Logger pour les requetes SQL (desactive par defaut)
        'django.db.backends': {
            'handlers': ['console'],
            'level': 'DEBUG' if LOG_SQL else 'WARNING',
            'propagate': False,
        },
        # Logger pour Celery
        'celery': {
            'handlers': ['console'],
            'level': LOG_LEVEL,
            'propagate': False,
        },
        # Logger pour l'audit
        'audit': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        # Logger pour les requetes HTTP (middleware)
        'http': {
            'handlers': ['console'],
            'level': LOG_LEVEL,
            'propagate': False,
        },
    },
}