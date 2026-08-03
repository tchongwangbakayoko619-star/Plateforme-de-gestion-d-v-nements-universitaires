# gather/inscriptions/apps.py
from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class InscriptionsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "gather.inscriptions"
    verbose_name = _("inscriptions")
