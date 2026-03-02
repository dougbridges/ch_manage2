"""
Tests for notification backends: ConsoleBackend, DjangoEmailBackend, backend loader.
"""


from django.core import mail
from django.test import TestCase, override_settings

from ..backends.console_backend import ConsoleBackend
from ..backends.email_backend import DjangoEmailBackend
from ..backends.loader import get_email_backend, get_sms_backend


class ConsoleBackendTest(TestCase):
    """Tests for the ConsoleBackend."""

    def test_send_email(self):
        backend = ConsoleBackend()
        result = backend.send_email("user@example.com", "Test", "<p>Hi</p>", "Hi")
        self.assertEqual(result, "console-email-user@example.com")

    def test_send_sms(self):
        backend = ConsoleBackend()
        result = backend.send_sms("+15551234567", "Hello via SMS")
        self.assertEqual(result, "console-sms-+15551234567")


class DjangoEmailBackendTest(TestCase):
    """Tests for the DjangoEmailBackend."""

    def test_send_email(self):
        backend = DjangoEmailBackend()
        result = backend.send_email("user@example.com", "Test Subject", "<p>Body</p>", "Body")
        self.assertIsNotNone(result)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, "Test Subject")
        self.assertEqual(mail.outbox[0].to, ["user@example.com"])

    def test_send_sms_not_implemented(self):
        backend = DjangoEmailBackend()
        with self.assertRaises(NotImplementedError):
            backend.send_sms("+15551234567", "Hello")


class BackendLoaderTest(TestCase):
    """Tests for the backend loader utility."""

    @override_settings(NOTIFICATION_EMAIL_BACKEND="apps.notifications.backends.console_backend.ConsoleBackend")
    def test_load_email_backend(self):
        backend = get_email_backend()
        self.assertIsInstance(backend, ConsoleBackend)

    @override_settings(NOTIFICATION_SMS_BACKEND="apps.notifications.backends.console_backend.ConsoleBackend")
    def test_load_sms_backend(self):
        backend = get_sms_backend()
        self.assertIsInstance(backend, ConsoleBackend)

    @override_settings(NOTIFICATION_EMAIL_BACKEND="apps.notifications.backends.email_backend.DjangoEmailBackend")
    def test_load_django_email_backend(self):
        backend = get_email_backend()
        self.assertIsInstance(backend, DjangoEmailBackend)
