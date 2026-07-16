from django.apps import AppConfig


class PlansConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.plans'
    verbose_name = 'Plans de Gestion'

    def ready(self):
        """Import signals when app is ready."""
        try:
            import apps.plans.signals  # noqa: F401
        except ImportError:
            pass