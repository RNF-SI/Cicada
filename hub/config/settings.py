"""
Configuration du hub d'exploration fédérée (#636).

Un seul module de réglages, contrairement à CICADA qui en a trois : le hub n'a
ni interface, ni comptes utilisateurs, ni envoi d'e-mails, ni tâches
asynchrones. Ce qui distingue le développement de la production tient dans
quelques variables d'environnement.
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def _bool(nom, defaut=False):
    brut = os.environ.get(nom)
    if brut is None:
        return defaut
    return brut.strip().lower() in ('1', 'true', 'vrai', 'oui', 'on')


def _liste(nom, defaut=''):
    return [v.strip() for v in os.environ.get(nom, defaut).split(',') if v.strip()]


# --------------------------------------------------------------------------- #
# Base
# --------------------------------------------------------------------------- #
SECRET_KEY = os.environ.get('SECRET_KEY', 'hub-secret-key-for-development')
DEBUG = _bool('DEBUG', True)
ALLOWED_HOSTS = _liste('ALLOWED_HOSTS', 'localhost,127.0.0.1,hub')

ROOT_URLCONF = 'config.urls'
WSGI_APPLICATION = 'config.wsgi.application'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

INSTALLED_APPS = [
    # `auth` et `contenttypes` ne servent à aucune fonctionnalité du hub : aucun
    # compte n'y est créé, l'authentification des instances passe par un jeton.
    # Ils restent installés parce que DRF résout `AnonymousUser` depuis
    # `django.contrib.auth.models`, ce qui exige l'app dans le registre.
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.gis',
    'django.contrib.postgres',
    'rest_framework',
    'apps.geo',
    'apps.nomenclatures',
    'apps.index',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.middleware.common.CommonMiddleware',
]

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {'context_processors': []},
    },
]

# --------------------------------------------------------------------------- #
# Base de données
# --------------------------------------------------------------------------- #
# Le `search_path` est plus court que celui de CICADA : le hub n'a ni
# utilisateurs, ni sites, ni plans, ni référentiels taxonomiques.
#
# `public` vient en TÊTE, contrairement à CICADA : tous les modèles du hub
# déclarent leur schéma dans `db_table`, si bien que le premier schéma du chemin
# ne reçoit que les tables internes de Django (`django_migrations`, `auth_*`).
# Leur place est dans `public` — les laisser tomber dans `ccd_search` ferait du
# schéma de l'index un fourre-tout.
DATABASES = {
    'default': {
        'ENGINE': 'django.contrib.gis.db.backends.postgis',
        'NAME': os.environ.get('POSTGRES_DB', 'cicada_hub'),
        'USER': os.environ.get('POSTGRES_USER', 'cicada_user'),
        'PASSWORD': os.environ.get('POSTGRES_PASSWORD', 'cicada_password'),
        'HOST': os.environ.get('POSTGRES_HOST', 'db'),
        'PORT': os.environ.get('POSTGRES_PORT', '5432'),
        'OPTIONS': {
            'options': '-c search_path=public,ccd_search,ref_geo,ref_nomenclatures'
        },
    }
}

# --------------------------------------------------------------------------- #
# Identité et fédération
# --------------------------------------------------------------------------- #
#: Identifiant du hub lui-même. Il ne produit aucun document : cette valeur ne
#: sert qu'à se nommer dans les réponses d'API et les journaux.
HUB_INSTANCE_ID = os.environ.get('HUB_INSTANCE_ID', 'hub')
HUB_INSTANCE_LABEL = os.environ.get('HUB_INSTANCE_LABEL', HUB_INSTANCE_ID)

#: Jetons acceptés pour le dépôt, **un par instance** :
#:     HUB_FEDERATION_TOKENS="rnf:jeton-rnf,cen:jeton-cen"
#: Un jeton par instance plutôt qu'un secret unique partagé, pour pouvoir en
#: révoquer un seul sans interrompre les autres. Volontairement rudimentaire :
#: l'authentification définitive dépend de #514 (OAuth2 / OIDC).
def _jetons(brut):
    jetons = {}
    for paire in brut.split(','):
        instance, _, jeton = paire.partition(':')
        instance, jeton = instance.strip(), jeton.strip()
        if instance and jeton:
            jetons[instance] = jeton
    return jetons


HUB_FEDERATION_TOKENS = _jetons(os.environ.get('HUB_FEDERATION_TOKENS', ''))

#: Jetons de lecture, **un par instance** :
#:     HUB_READ_TOKENS="rnf:lecture-rnf,cen:lecture-cen"
#: Un secret partagé aurait suffi à authentifier, mais pas à *identifier* : la
#: réciprocité (#636) exige de savoir qui lit pour vérifier qu'il publie aussi.
#: Distincts des jetons de dépôt — lire n'est pas écrire, et révoquer l'un ne
#: doit pas emporter l'autre.
HUB_READ_TOKENS = _jetons(os.environ.get('HUB_READ_TOKENS', ''))

# --------------------------------------------------------------------------- #
# API
# --------------------------------------------------------------------------- #
REST_FRAMEWORK = {
    # Aucune authentification de session ni de compte : les appelants sont des
    # serveurs, identifiés par jeton au niveau des permissions de chaque vue.
    'DEFAULT_AUTHENTICATION_CLASSES': [],
    'DEFAULT_PERMISSION_CLASSES': [],
    'UNAUTHENTICATED_USER': None,
}

# --------------------------------------------------------------------------- #
# Divers
# --------------------------------------------------------------------------- #
LANGUAGE_CODE = 'fr-fr'
TIME_ZONE = 'Europe/Paris'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'simple': {'format': '[{asctime}] {levelname} {name} — {message}',
                   'style': '{'},
    },
    'handlers': {
        'console': {'class': 'logging.StreamHandler', 'formatter': 'simple'},
    },
    'root': {'handlers': ['console'], 'level': os.environ.get('LOG_LEVEL', 'INFO')},
}
