"""
Backend loader utility.

Loads notification backends from the paths configured in Django settings.
"""

from importlib import import_module

from django.conf import settings

from .base import NotificationBackend


def _load_backend(dotted_path: str) -> NotificationBackend:
    """Import and instantiate a backend from its dotted Python path."""
    module_path, class_name = dotted_path.rsplit(".", 1)
    module = import_module(module_path)
    backend_class = getattr(module, class_name)
    return backend_class()


def get_email_backend() -> NotificationBackend:
    """Return the configured email notification backend."""
    path = getattr(
        settings,
        "NOTIFICATION_EMAIL_BACKEND",
        "apps.notifications.backends.console_backend.ConsoleBackend",
    )
    return _load_backend(path)


def get_sms_backend() -> NotificationBackend:
    """Return the configured SMS notification backend."""
    path = getattr(
        settings,
        "NOTIFICATION_SMS_BACKEND",
        "apps.notifications.backends.console_backend.ConsoleBackend",
    )
    return _load_backend(path)
