"""
Configuration de l'app authentication.
"""
from django.apps import AppConfig


class AuthenticationConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.authentication'
    verbose_name = 'Authentification'

    def ready(self):
        from . import checks  # noqa: F401 — enregistre les vérifications du mode de connexion
