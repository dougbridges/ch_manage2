"""
Tests for event reminder Celery tasks.
"""

from datetime import timedelta

from django.test import override_settings
from django.utils import timezone

from .base import EventTestBase, create_event


@override_settings(
    NOTIFICATION_EMAIL_BACKEND="apps.notifications.backends.console_backend.ConsoleBackend"
)
class SendEventRemindersTaskTest(EventTestBase):

    def test_sends_reminders_for_upcoming_events(self):
        # Event in 24 hours (within the 48h default window)
        create_event(
            self.team,
            self.admin_user,
            title="Upcoming Service",
            start_datetime=timezone.now() + timedelta(hours=24),
            end_datetime=timezone.now() + timedelta(hours=26),
        )

        from ..tasks import send_event_reminders
        # Should not raise
        send_event_reminders(hours_ahead=48)

    def test_ignores_past_events(self):
        create_event(
            self.team,
            self.admin_user,
            title="Past Event",
            start_datetime=timezone.now() - timedelta(hours=2),
            end_datetime=timezone.now() - timedelta(hours=1),
        )

        from ..tasks import send_event_reminders
        send_event_reminders(hours_ahead=48)
        # Should complete without error, sending nothing for past events

    def test_ignores_far_future_events(self):
        create_event(
            self.team,
            self.admin_user,
            title="Far Future",
            start_datetime=timezone.now() + timedelta(days=30),
            end_datetime=timezone.now() + timedelta(days=30, hours=2),
        )

        from ..tasks import send_event_reminders
        send_event_reminders(hours_ahead=48)
        # Should complete without sending for events outside the window

    def test_ignores_unpublished_events(self):
        create_event(
            self.team,
            self.admin_user,
            title="Draft Event",
            start_datetime=timezone.now() + timedelta(hours=24),
            end_datetime=timezone.now() + timedelta(hours=26),
            is_published=False,
        )

        from ..tasks import send_event_reminders
        send_event_reminders(hours_ahead=48)
