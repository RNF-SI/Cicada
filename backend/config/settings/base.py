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

# Mode de connexion de l'instance — UN SEUL à la fois, jamais en parallèle (#689) :
# - 'local' (défaut) : comptes CICADA (email + mot de passe, inscription, mot de
#   passe oublié) ;
# - 'geonature' : comptes d'un GeoNature / UsersHub uniquement (réglages
#   GEONATURE_AUTH_* ci-dessous) ; connexion par mot de passe CICADA,
#   inscription et réinitialisation coupées ;
# - 'keycloak' : historique, gestion RGPD des comptes déléguée (non branché).
AUTH_PROVIDER = os.environ.get('AUTH_PROVIDER', 'local').strip().lower() or 'local'

# ---------------------------------------------------------------------------
# Connexion par un GeoNature / UsersHub (#689, #691) — AUTH_PROVIDER='geonature'
# ---------------------------------------------------------------------------
# Lus seulement en mode 'geonature' ; en mode 'local', l'instance n'appelle
# jamais GeoNature.
# GeoNature >= 2.17.0 requis pour rattacher le compte à son organisme
# (GET <API>/users/organism/<id>) ; en dessous, la connexion fonctionne sans.
# Adresse de l'API GeoNature (son API_ENDPOINT), ex. https://geonature.exemple.fr/api
GEONATURE_AUTH_URL = os.environ.get('GEONATURE_AUTH_URL', '').strip().rstrip('/')
GEONATURE_AUTH_ID_APPLICATION = os.environ.get('GEONATURE_AUTH_ID_APPLICATION', '').strip()
# Libellé du bouton de connexion (« RNF », « GeoNature »…).
GEONATURE_AUTH_LIBELLE = os.environ.get('GEONATURE_AUTH_LIBELLE', 'GeoNature').strip()
GEONATURE_AUTH_TIMEOUT = int(os.environ.get('GEONATURE_AUTH_TIMEOUT', '10'))
# id_organisme UsersHub qui ne sont pas de vrais organismes (« Autre », « ALL »,
# comptes de test…) : le compte entre sans organisme. Ex. « -1,2,303,339 ».
GEONATURE_AUTH_ORGANISMES_EXCLUS = {
    int(x) for x in os.environ.get('GEONATURE_AUTH_ORGANISMES_EXCLUS', '').split(',')
    if x.strip().lstrip('-').isdigit()
}
# Comment les comptes UsersHub sont vérifiés (#764) :
# - 'api' (défaut) : par l'API du GeoNature ci-dessus. GeoNature ne contrôle
#   que le droit sur LUI-MÊME (son CODE_APPLICATION), jamais sur CICADA — et
#   pas du tout avec pypnusershub <= 3.2 (bug : tout compte entre) ;
# - 'base' : CICADA lit la base UsersHub (lecture seule) et contrôle le droit
#   sur SON application (GEONATURE_AUTH_CODE_APPLICATION). GEONATURE_AUTH_URL
#   ne sert alors plus.
GEONATURE_AUTH_SOURCE = os.environ.get('GEONATURE_AUTH_SOURCE', 'api').strip().lower() or 'api'
GEONATURE_AUTH_CODE_APPLICATION = os.environ.get('GEONATURE_AUTH_CODE_APPLICATION', '').strip()
# Base UsersHub (en général celle de GeoNature), compte en lecture seule
# limité aux colonnes utiles : packaging/debian/usr/bin/cicada-usershub-lecture.
USERSHUB_DB_HOST = os.environ.get('USERSHUB_DB_HOST', '').strip()
USERSHUB_DB_PORT = int(os.environ.get('USERSHUB_DB_PORT', '5432') or 5432)
USERSHUB_DB_NAME = os.environ.get('USERSHUB_DB_NAME', '').strip()
USERSHUB_DB_USER = os.environ.get('USERSHUB_DB_USER', '').strip()
USERSHUB_DB_PASSWORD = os.environ.get('USERSHUB_DB_PASSWORD', '')
# Chiffrement de la connexion (valeurs de libpq). « prefer » (défaut) chiffre si
# le serveur le propose, sans l'exiger : suffisant quand la base est sur le même
# serveur. Base distante : « require » au moins, « verify-full » avec
# USERSHUB_DB_SSLROOTCERT (certificat de l'autorité, monté dans le conteneur)
# pour vérifier aussi le nom du serveur.
USERSHUB_DB_SSLMODE = os.environ.get('USERSHUB_DB_SSLMODE', 'prefer').strip().lower() or 'prefer'
USERSHUB_DB_SSLROOTCERT = os.environ.get('USERSHUB_DB_SSLROOTCERT', '').strip()
# Schéma des tables UsersHub (« utilisateurs » partout ; réglable pour les tests,
# la base de CICADA ayant elle aussi un schéma « utilisateurs »).
USERSHUB_DB_SCHEMA = os.environ.get('USERSHUB_DB_SCHEMA', 'utilisateurs').strip() or 'utilisateurs'

# ---------------------------------------------------------------------------
# Identité de l'instance (#636 — exploration fédérée)
# ---------------------------------------------------------------------------
# CICADA est déployé en plusieurs instances, chacune avec sa propre base. Aucun
# identifiant applicatif n'étant unique entre déploiements (id_pg, slug, ids
# d'organismes… sont des séquences locales), tout document publié vers
# l'exploration centralisée doit porter son instance d'origine.
#
# `or` et non un défaut de `get` : la variable est souvent *définie mais vide*
# (fichier .env où la ligne existe sans valeur, docker-compose qui transmet une
# chaîne vide). Une identité vide est pire qu'absente — elle s'écrit dans chaque
# ligne d'index, où elle passe inaperçue, et aucune publication ne retrouve
# ensuite ces documents.
CICADA_INSTANCE_ID = os.environ.get('CICADA_INSTANCE_ID') or 'local'
# Nom de l'instance tel qu'il s'affiche chez les autres structures (provenance
# des résultats et des plans distants). Pas de repli sur l'identifiant : un
# « rnf » ne dit rien à un gestionnaire, et la publication refuse un nom vide.
CICADA_INSTANCE_LABEL = (
    os.environ.get('CICADA_INSTANCE_LABEL') or ''
)

# Jeton partagé pour l'authentification machine-à-machine entre instances.
# Volontairement rudimentaire : l'authentification fédérée est une question
# ouverte de #636, qui dépend de #514 (OAuth2 / OIDC). Un jeton partagé permet
# de tester la mécanique sans préjuger de la solution retenue.
CICADA_FEDERATION_TOKEN = os.environ.get('CICADA_FEDERATION_TOKEN', '')

# URL publique de cette instance, transmise avec chaque plan publié. Elle permet
# au hub de renvoyer un utilisateur vers le plan chez son gestionnaire — pour ce
# que le hub ne porte pas : pièces jointes, édition, données non explorables.
CICADA_PUBLIC_URL = os.environ.get('CICADA_PUBLIC_URL', '')

# ---------------------------------------------------------------------------
# Hub d'exploration fédérée (#636)
# ---------------------------------------------------------------------------
# Le hub agrège l'index de plusieurs instances et sert la recherche transverse.
# Ces réglages sont vides par défaut : sans eux, l'instance ne publie rien et
# sert son exploration depuis son propre index, comme avant.
CICADA_HUB_URL = os.environ.get('CICADA_HUB_URL', '').rstrip('/')

#: Jeton de dépôt, propre à cette instance (côté hub : `HUB_FEDERATION_TOKENS`).
CICADA_HUB_PUSH_TOKEN = os.environ.get('CICADA_HUB_PUSH_TOKEN', '')

#: Jeton de lecture, partagé (côté hub : `HUB_READ_TOKEN`).
CICADA_HUB_READ_TOKEN = os.environ.get('CICADA_HUB_READ_TOKEN', '')

#: D'où l'exploration tire ses résultats : `local` (l'index de cette base) ou
#: `hub` (l'index agrégé). Le basculement est un réglage et non un déploiement,
#: pour qu'un retour arrière soit immédiat si le hub se révèle indisponible ou
#: incomplet. À terme l'index local disparaît et ce réglage avec lui.
CICADA_EXPLORATION_SOURCE = os.environ.get('CICADA_EXPLORATION_SOURCE', 'local')

#: La publication vers le hub est-elle automatique (tâche planifiée de nuit) ?
#: Réglage distinct de l'URL du hub : une instance peut vouloir *lire*
#: l'exploration nationale — ce qui exige l'URL — sans publier autrement qu'à la
#: main. La publication reste par ailleurs conditionnée au consentement de la
#: structure (`SiteConfiguration.federation_partage`, faux par défaut).
CICADA_HUB_PUSH_AUTO = (
    os.environ.get('CICADA_HUB_PUSH_AUTO', 'true').strip().lower()
    in ('1', 'true', 'vrai', 'oui', 'on')
)

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.gis',
    'django.contrib.postgres',
    'rest_framework',
    'drf_spectacular',
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
    'apps.geo',
    'apps.search',
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
            'options': '-c search_path=utilisateurs,referentiels,ref_nomenclatures,ref_geo,general,fichiers,ccd_commons,ccd_notifications,ccd_search,taxonomie,ref_habitats,ref_inpg,ref_campanule,public'
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
    'ACCESS_TOKEN_LIFETIME': timedelta(days=7),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=30),
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
    # Schéma OpenAPI généré depuis les ViewSets/serializers (drf-spectacular).
    # Alimente /api/schema/, /api/docs/ et la référence des endpoints de la
    # documentation (documentation/docs/api/openapi.json, voir scripts/export-openapi.sh).
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_THROTTLE_CLASSES': [
        'apps.authentication.throttles.ResilientAnonRateThrottle',
        'apps.authentication.throttles.ResilientUserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '200/hour',
        'user': '5000/hour',
        'auth': '5/minute',
    },
}

# drf-spectacular — schéma OpenAPI 3 de l'API.
# Le schéma décrit l'API d'une instance ; la documentation statique (/aide/)
# en embarque une copie générée par `manage.py spectacular`.
SPECTACULAR_SETTINGS = {
    'TITLE': 'API CICADA',
    'DESCRIPTION': (
        "API REST de CICADA — gestion des plans de gestion d'espaces naturels protégés. "
        "Tous les endpoints exigent un jeton JWT, sauf /api/auth/, /api/health/ et "
        "l'API publique des métadonnées des plans (/api/public/) lorsque l'instance l'a ouverte."
    ),
    'VERSION': None,  # version lue dans version.txt par config.version, pas dupliquée ici
    'SERVE_INCLUDE_SCHEMA': False,
    # Le hook enums est celui par défaut ; le second donne un résumé aux opérations
    # qui n'en ont pas (première phrase de la docstring), voir config/spectacular.py.
    'POSTPROCESSING_HOOKS': [
        'drf_spectacular.hooks.postprocess_schema_enums',
        'config.spectacular.resume_depuis_description',
    ],
    # #750 — Swagger UI (/api/docs/) et le schéma s'ouvrent sans connexion : le
    # navigateur n'envoie jamais le JWT de l'application à cette page, qui
    # répondait toujours 401. Le schéma est déjà public dans /aide/api/ ; les
    # appels, eux, restent protégés (jeton saisi dans « Authorize »).
    'SERVE_PERMISSIONS': ['rest_framework.permissions.AllowAny'],
    'COMPONENT_SPLIT_REQUEST': True,
    'SCHEMA_PATH_PREFIX': r'/api/',
    'SCHEMA_PATH_PREFIX_TRIM': False,
    'SWAGGER_UI_SETTINGS': {'docExpansion': 'list', 'filter': True, 'persistAuthorization': True},
    # Plusieurs modèles ont un champ `statut` avec des choix différents : sans
    # nom explicite, drf-spectacular génère `Statut9e9Enum` / `Statut35dEnum`.
    'ENUM_NAME_OVERRIDES': {
        'PlanStatutEnum': 'apps.plans.models.PlanGestion.STATUT_CHOICES',
        'PlanValidationStepEnum': 'apps.plans.models.PlanGestion.VALIDATION_STEP_CHOICES',
        'OperationStatutEnum': 'apps.plans.models_operations.Operation.STATUT_CHOICES',
        'ValidationRequestStatusEnum': 'apps.notifications.models.ValidationRequest.STATUS_CHOICES',
        # Enveloppes GeoJSON documentaires (config/spectacular.py) : champ `type` constant.
        'GeoJSONFeatureTypeEnum': 'config.spectacular.GEOJSON_FEATURE_TYPE_CHOICES',
        'GeoJSONFeatureCollectionTypeEnum': 'config.spectacular.GEOJSON_FEATURE_COLLECTION_TYPE_CHOICES',
        'GeoJSONCrsTypeEnum': 'config.spectacular.GEOJSON_CRS_TYPE_CHOICES',
    },
    'TAGS': [
        {'name': 'auth', 'description': 'Authentification JWT, inscription, profil courant'},
        {'name': 'users', 'description': 'Utilisateurs, organismes, sites'},
        {'name': 'plans', 'description': 'Plans de gestion et leur contenu'},
        {'name': 'inventaires', 'description': 'Inventaires et suivis scientifiques'},
        {'name': 'exploration', 'description': 'Exploration des données des plans'},
        {'name': 'public', 'description': 'API publique des métadonnées des plans (#645)'},
        {'name': 'notifications', 'description': "Notifications in-app de l'utilisateur connecté"},
        {'name': 'validations', 'description': 'Demandes de validation (inscriptions, accès, liens site-plan)'},
        {'name': 'activity', 'description': "Historique d'activité"},
        {'name': 'modules', 'description': 'Modules applicatifs'},
        {'name': 'nomenclatures', 'description': 'Nomenclatures (listes de référence)'},
        {'name': 'settings', 'description': "Paramètres de l'instance (configuration du site)"},
        {'name': 'admin', 'description': 'Administration : orphelins, logs applicatifs, journal des erreurs'},
    ],
}

# CORS settings
CORS_ALLOW_ALL_ORIGINS = DEBUG
CORS_ALLOWED_ORIGINS = os.environ.get('CORS_ALLOWED_ORIGINS', '').split(',') if os.environ.get('CORS_ALLOWED_ORIGINS') else []

# Celery Configuration
CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', 'redis://redis:6379/0')
CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', 'redis://redis:6379/1')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60  # 30 minutes

# Celery Beat - Taches periodiques
from celery.schedules import crontab

from config.creneau import creneau_publication

_CRENEAU_PUBLICATION = creneau_publication(CICADA_INSTANCE_ID)

CELERY_BEAT_SCHEDULE = {
    # Nettoyage des anciens logs d'erreur - tous les jours a 3h du matin
    'cleanup-old-error-logs': {
        'task': 'core.cleanup_old_error_logs',
        'schedule': crontab(hour=3, minute=0),
        'kwargs': {'days': 90, 'acknowledged_days': 30},
    },
    # #328 - L'audit hebdomadaire des organismes sans admin (recap email du lundi)
    # a ete supprime : etat persistant detecte en temps reel par les signaux
    # Django (users/signals.py), pas un evenement a renvoyer chaque semaine.
    # Note: Les sites et plans orphelins ne sont plus audites par email hebdomadaire.
    # L'etat orphelin est un etat persistant (et non un evenement) : il est consultable
    # a la demande via la page Administration > Orphelins (endpoint /api/admin/orphans/).
    # La detection temps reel d'un site qui devient orphelin reste assuree par les signaux
    # Django (in-app uniquement, sans email).
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
    # #636 - Publication de l'index vers le hub d'exploration federee, chaque
    # nuit. La tache ne fait rien si le hub n'est pas configure, si
    # CICADA_HUB_PUSH_AUTO est faux, ou si la structure n'a pas consenti au
    # partage : l'entree peut donc rester en place sur toutes les instances.
    # Un depot complet et non un differentiel - une nuit sautee ne perd rien.
    # #701 - Heure propre a chaque instance (entre 1h00 et 5h00, derivee de
    # CICADA_INSTANCE_ID) : toutes a 2h30, elles saturaient le hub ensemble.
    'push-federation': {
        'task': 'apps.search.tasks.publier_vers_le_hub',
        'schedule': crontab(
            hour=_CRENEAU_PUBLICATION[0], minute=_CRENEAU_PUBLICATION[1],
        ),
    },
    # #696 - Relecture aupres de l'API de suivi d'une demande d'adhesion au hub
    # en attente (acceptee ou refusee par RNF dans l'admin du suivi). Ne fait
    # rien hors attente : sans demande, aucun appel reseau.
    'actualiser-adhesion-hub': {
        'task': 'apps.search.tasks.actualiser_adhesion_hub',
        'schedule': crontab(minute='*/30'),
    },
    # Retrait du hub en attente : le partage a ete decoche alors que le hub
    # etait injoignable. Relance chaque heure ; sans retrait en attente, la
    # tache ne fait rien (aucun appel reseau).
    'relancer-retrait-hub': {
        'task': 'apps.search.tasks.relancer_retrait_hub',
        'schedule': crontab(minute=15),
    },
    # Note: Le traitement des demandes RGPD est maintenant manuel via l'interface admin
    # Les super_admins decident quand desactiver ou anonymiser les comptes
}

# Fond de carte des cartes incluses aux exports (#629)
# Gabarit XYZ ({z}/{x}/{y}). Laisser vide pour desactiver le fond de carte
# (les emprises sont alors dessinees sur un aplat, comme avant #629).
EXPORT_MAP_TILE_URL = os.environ.get(
    'EXPORT_MAP_TILE_URL', 'https://tile.openstreetmap.org/{z}/{x}/{y}.png'
)
EXPORT_MAP_ATTRIBUTION = os.environ.get('EXPORT_MAP_ATTRIBUTION', '© OpenStreetMap')

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