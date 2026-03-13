from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class CampanuleConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.campanule'
    verbose_name = _("CAMPanule (Protocoles)")
