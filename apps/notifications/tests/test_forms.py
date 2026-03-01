"""
Tests for notification forms: BlastComposeForm, ContactPreferenceForm.
"""

from django.test import TestCase

from ..forms import BlastComposeForm, ContactPreferenceForm
from ..models import NotificationChannel


class BlastComposeFormTest(TestCase):
    """Tests for the BlastComposeForm."""

    def test_valid_email_blast(self):
        form = BlastComposeForm(data={
            "subject": "Test Subject",
            "body": "Test body content.",
            "channel": NotificationChannel.EMAIL,
        })
        self.assertTrue(form.is_valid())

    def test_email_blast_requires_subject(self):
        form = BlastComposeForm(data={
            "subject": "",
            "body": "Test body content.",
            "channel": NotificationChannel.EMAIL,
        })
        self.assertFalse(form.is_valid())
        self.assertIn("subject", form.errors)

    def test_sms_blast_no_subject_required(self):
        form = BlastComposeForm(data={
            "subject": "",
            "body": "Quick SMS update.",
            "channel": NotificationChannel.SMS,
        })
        self.assertTrue(form.is_valid())

    def test_missing_body(self):
        form = BlastComposeForm(data={
            "subject": "Test",
            "body": "",
            "channel": NotificationChannel.EMAIL,
        })
        self.assertFalse(form.is_valid())
        self.assertIn("body", form.errors)


class ContactPreferenceFormTest(TestCase):
    """Tests for the ContactPreferenceForm."""

    def test_valid_email_only(self):
        form = ContactPreferenceForm(data={
            "receive_email": True,
            "receive_sms": False,
            "phone_number": "",
        })
        self.assertTrue(form.is_valid())

    def test_sms_requires_phone(self):
        form = ContactPreferenceForm(data={
            "receive_email": True,
            "receive_sms": True,
            "phone_number": "",
        })
        self.assertFalse(form.is_valid())
        self.assertIn("phone_number", form.errors)

    def test_valid_sms_with_phone(self):
        form = ContactPreferenceForm(data={
            "receive_email": True,
            "receive_sms": True,
            "phone_number": "+15551234567",
        })
        self.assertTrue(form.is_valid())

    def test_phone_without_sms_is_fine(self):
        form = ContactPreferenceForm(data={
            "receive_email": True,
            "receive_sms": False,
            "phone_number": "+15551234567",
        })
        self.assertTrue(form.is_valid())
