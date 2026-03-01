"""
Tests for event forms: validation, field rendering.
"""

from django.test import TestCase
from django.utils import timezone

from ..forms import EventForm, VolunteerSlotForm


class EventFormTest(TestCase):
    def test_valid_form(self):
        start = timezone.now() + timezone.timedelta(days=1)
        end = start + timezone.timedelta(hours=2)
        data = {
            "title": "Test Event",
            "start_datetime": start.strftime("%Y-%m-%dT%H:%M"),
            "end_datetime": end.strftime("%Y-%m-%dT%H:%M"),
            "category": "worship",
            "is_published": True,
        }
        form = EventForm(data)
        self.assertTrue(form.is_valid())

    def test_end_before_start_invalid(self):
        start = timezone.now() + timezone.timedelta(days=1)
        end = start - timezone.timedelta(hours=1)
        data = {
            "title": "Bad Dates",
            "start_datetime": start.strftime("%Y-%m-%dT%H:%M"),
            "end_datetime": end.strftime("%Y-%m-%dT%H:%M"),
            "category": "other",
        }
        form = EventForm(data)
        self.assertFalse(form.is_valid())

    def test_missing_title_invalid(self):
        start = timezone.now() + timezone.timedelta(days=1)
        end = start + timezone.timedelta(hours=2)
        data = {
            "start_datetime": start.strftime("%Y-%m-%dT%H:%M"),
            "end_datetime": end.strftime("%Y-%m-%dT%H:%M"),
            "category": "other",
        }
        form = EventForm(data)
        self.assertFalse(form.is_valid())
        self.assertIn("title", form.errors)


class VolunteerSlotFormTest(TestCase):
    def test_valid_form(self):
        data = {"role_name": "Ushers", "slots_needed": 3}
        form = VolunteerSlotForm(data)
        self.assertTrue(form.is_valid())

    def test_missing_role_name_invalid(self):
        data = {"slots_needed": 3}
        form = VolunteerSlotForm(data)
        self.assertFalse(form.is_valid())
        self.assertIn("role_name", form.errors)
