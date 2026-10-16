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
        # Extensions drf-spectacular (géométries PostGIS, GeoJSON) : elles
        # s'enregistrent à l'import, avant toute génération du schéma.
        import config.spectacular  # noqa: F401