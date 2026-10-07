"""
Django settings for tracking API project.
"""
import os
from pathlib import Path
from decouple import config

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config('SECRET_KEY', default='django-insecure-change-me-in-production')
DEBUG = config('DEBUG', default=False, cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost').split(',')
# Derrière Apache en HTTPS : confiance à l’origine réelle et reconnaissance du proxy
CSRF_TRUSTED_ORIGINS = [
    'https://tracking.cicada.reserves-naturelles.org',
]
# Indiquer à Django que la requête était en HTTPS (Apache envoie X-Forwarded-Proto)
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'instances',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'tracking.urls'

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

WSGI_APPLICATION = 'tracking.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('DB_NAME', default='tracking'),
        'USER': config('DB_USER', default='tracking_user'),
        'PASSWORD': config('DB_PASSWORD', default=''),
        'HOST': config('DB_HOST', default='localhost'),
        'PORT': config('DB_PORT', default='5432'),
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

LANGUAGE_CODE = 'fr-fr'
TIME_ZONE = 'Europe/Paris'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'static')

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'instances.authentication.InstanceTokenAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '10/hour',
        'user': '100/hour',
    }
}

# Dernière version publiée de CICADA, annoncée aux instances par le heartbeat.
# Vide = aucune mise à jour annoncée (plutôt qu'une valeur fictive, qui faisait
# signaler une « mise à jour disponible » à toutes les instances).
LATEST_VERSION = config('LATEST_VERSION', default='')

# Hub d'exploration fédérée (#696) : l'API de suivi enrôle les instances dont
# l'adhésion est confirmée par code. HUB_ADMIN_TOKEN est le même que celui du
# hub ; vides = la confirmation échoue (hub_injoignable), rien n'est enrôlé.
HUB_URL = config('HUB_URL', default='')
HUB_ADMIN_TOKEN = config('HUB_ADMIN_TOKEN', default='')

# Adhésion au hub : e-mails (#696). RNF reçoit les nouvelles demandes et les
# messages du formulaire de contact ; ADMIN_BASE_URL sert au lien vers la fiche
# de la demande dans l'e-mail (vide = chemin relatif seul).
RNF_CONTACT_EMAIL = config('RNF_CONTACT_EMAIL', default='si@rnfrance.org')
ADMIN_BASE_URL = config('ADMIN_BASE_URL', default='')
EMAIL_BACKEND = config('EMAIL_BACKEND', default='django.core.mail.backends.smtp.EmailBackend')
EMAIL_HOST = config('EMAIL_HOST', default='localhost')
EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='noreply@cicada.reserves-naturelles.org')
# Les envois sont synchrones (dans la requête de l'instance, ou de l'admin) :
# un serveur SMTP muet ne doit pas figer la page.
EMAIL_TIMEOUT = config('EMAIL_TIMEOUT', default=10, cast=int)
