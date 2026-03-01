"""
AppConfig for the events app.
"""

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class EventsConfig(AppConfig):
    default_auto_field = "django.db.models.AutoField"
    name = "apps.events"
    verbose_name = _("Events")
