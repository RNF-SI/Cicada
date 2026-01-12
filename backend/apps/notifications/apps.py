"""
Configuration de l'application notifications.
"""
from django.apps import AppConfig


class NotificationsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.notifications'
    verbose_name = 'Notifications et Validations'

    def ready(self):
        """Import signals when app is ready."""
        try:
            import apps.notifications.signals  # noqa: F401
        except ImportError:
            pass
