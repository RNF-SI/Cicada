from django.apps import AppConfig


class GeoConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.geo'
    verbose_name = 'Référentiel géographique (ref_geo)'

    def ready(self):
        # Enregistre le signal de recalcul du rattachement administratif
        # des sites (cf. apps/geo/signals.py).
        from . import signals  # noqa: F401
