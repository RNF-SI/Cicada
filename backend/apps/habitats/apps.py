from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class HabitatsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.habitats'
    verbose_name = _("Habitats (HabRef)")
