# gather/events/apps.py
from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class EventsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "gather.events"
    verbose_name = _("Événements")

    def ready(self):
        import gather.events.signals  # noqa: F401, PLC0415
