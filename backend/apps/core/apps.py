"""
Configuration de l'app core.
"""
from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.core'
    verbose_name = 'Core'

    def ready(self):
        """Import activity signals when app is ready."""
        import apps.core.activity_signals  # noqa: F401