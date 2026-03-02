"""
Tests for event notification helpers: announcements, updates, and signup confirmations.
"""

from unittest.mock import patch

from django.test import override_settings

from apps.notifications.models import ContactPreference

from ..models import SignupStatus, VolunteerSignup
from ..notifications import notify_event_created, notify_event_updated, notify_signup_confirmation
from .base import EventTestBase, create_event, create_slot, create_signup


@override_settings(
    NOTIFICATION_EMAIL_BACKEND="apps.notifications.backends.console_backend.ConsoleBackend"
)
class NotifyEventCreatedTest(EventTestBase):

    def test_sends_to_all_members(self):
        event = create_event(self.team, self.admin_user)
        count = notify_event_created(event)
        # admin, coordinator, member = 3 team members
        self.assertEqual(count, 3)

    def test_skips_unpublished_events(self):
        event = create_event(self.team, self.admin_user, is_published=False)
        count = notify_event_created(event)
        self.assertIsNone(count)

    def test_respects_email_opt_out(self):
        ContactPreference.objects.create(
            team=self.team, user=self.member_user, receive_email=False
        )
        event = create_event(self.team, self.admin_user)
        count = notify_event_created(event)
        self.assertEqual(count, 2)  # member opted out


@override_settings(
    NOTIFICATION_EMAIL_BACKEND="apps.notifications.backends.console_backend.ConsoleBackend"
)
class NotifyEventUpdatedTest(EventTestBase):

    def test_notifies_signed_up_volunteers(self):
        event = create_event(self.team, self.admin_user)
        slot = create_slot(event)
        create_signup(slot, self.member_user)

        count = notify_event_updated(event, ["Time changed to 10:00 AM"])
        self.assertEqual(count, 1)

    def test_no_notification_when_no_signups(self):
        event = create_event(self.team, self.admin_user)
        count = notify_event_updated(event, ["Location changed"])
        self.assertEqual(count, 0)

    def test_deduplicates_multiple_signups(self):
        event = create_event(self.team, self.admin_user)
        slot1 = create_slot(event, role_name="Ushers")
        slot2 = create_slot(event, role_name="Nursery")
        create_signup(slot1, self.member_user)
        create_signup(slot2, self.member_user)

        count = notify_event_updated(event, ["Time changed"])
        self.assertEqual(count, 1)  # same user, only one email

    def test_ignores_cancelled_signups(self):
        event = create_event(self.team, self.admin_user)
        slot = create_slot(event)
        create_signup(slot, self.member_user, status=SignupStatus.CANCELLED)

        count = notify_event_updated(event, ["Location changed"])
        self.assertEqual(count, 0)


@override_settings(
    NOTIFICATION_EMAIL_BACKEND="apps.notifications.backends.console_backend.ConsoleBackend"
)
class NotifySignupConfirmationTest(EventTestBase):

    def test_sends_confirmation(self):
        event = create_event(self.team, self.admin_user)
        slot = create_slot(event)
        signup = create_signup(slot, self.member_user)

        result = notify_signup_confirmation(signup)
        self.assertTrue(result)

    def test_handles_failure_gracefully(self):
        event = create_event(self.team, self.admin_user)
        slot = create_slot(event)
        signup = create_signup(slot, self.member_user)

        with patch(
            "apps.events.notifications.get_email_backend",
            side_effect=Exception("backend error"),
        ):
            result = notify_signup_confirmation(signup)
            self.assertFalse(result)
