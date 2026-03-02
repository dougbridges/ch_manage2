"""
Integration tests: end-to-end notification flow covering events + notifications + volunteers.
"""

from datetime import timedelta
from unittest.mock import patch

from django.test import override_settings
from django.utils import timezone

from apps.events.models import Event, EventCategory, VolunteerSlot, VolunteerSignup
from apps.events.notifications import notify_event_created, notify_event_updated
from apps.notifications.models import (
    BlastStatus,
    ContactPreference,
    MessageBlast,
    MessageRecipient,
    NotificationChannel,
    RecipientStatus,
)
from apps.volunteers.models import RotationSchedule, RotationStrategy, ScheduledShift, ShiftStatus, VolunteerProfile

from .base import NotificationTestBase, create_blast, create_preference, create_recipient


@override_settings(
    NOTIFICATION_EMAIL_BACKEND="apps.notifications.backends.console_backend.ConsoleBackend",
    NOTIFICATION_SMS_BACKEND="apps.notifications.backends.console_backend.ConsoleBackend",
)
class FullNotificationFlowTest(NotificationTestBase):
    """End-to-end: create blast, add recipients, send, verify delivery status."""

    @patch("apps.notifications.tasks.send_single_notification.delay")
    def test_blast_send_flow(self, mock_delay):
        blast = create_blast(self.team, self.admin_user)
        r1 = create_recipient(blast, self.member_user)
        r2 = create_recipient(blast, self.coordinator_user)

        from apps.notifications.tasks import send_blast
        send_blast(blast.pk)

        blast.refresh_from_db()
        self.assertEqual(blast.status, BlastStatus.SENT)
        self.assertEqual(mock_delay.call_count, 2)

    def test_single_notification_email_delivery(self):
        blast = create_blast(self.team, self.admin_user, channel=NotificationChannel.EMAIL)
        recipient = create_recipient(blast, self.member_user)

        from apps.notifications.tasks import send_single_notification
        send_single_notification(recipient.pk)

        recipient.refresh_from_db()
        self.assertEqual(recipient.status, RecipientStatus.SENT)

    def test_contact_preference_respected_in_blast(self):
        """If a member opts out of email, they shouldn't receive blast recipients."""
        create_preference(self.team, self.member_user, receive_email=False)
        create_preference(self.team, self.coordinator_user, receive_email=True)

        event = Event.objects.create(
            team=self.team,
            title="Test Event",
            start_datetime=timezone.now() + timedelta(days=1),
            end_datetime=timezone.now() + timedelta(days=1, hours=2),
            category=EventCategory.WORSHIP,
            created_by=self.admin_user,
            is_published=True,
        )
        count = notify_event_created(event)
        # admin (no pref, defaults to email) + coordinator (opted in) = 2
        # member opted out
        self.assertEqual(count, 2)


@override_settings(
    NOTIFICATION_EMAIL_BACKEND="apps.notifications.backends.console_backend.ConsoleBackend"
)
class EventVolunteerNotificationTest(NotificationTestBase):
    """Integration: event updates notify signed-up volunteers."""

    def test_event_update_notifies_volunteers(self):
        event = Event.objects.create(
            team=self.team,
            title="Worship Service",
            start_datetime=timezone.now() + timedelta(days=1),
            end_datetime=timezone.now() + timedelta(days=1, hours=2),
            category=EventCategory.WORSHIP,
            created_by=self.admin_user,
            is_published=True,
        )
        slot = VolunteerSlot.objects.create(
            event=event, team=self.team, role_name="Ushers", slots_needed=3
        )
        VolunteerSignup.objects.create(
            slot=slot, volunteer=self.member_user, team=self.team
        )
        VolunteerSignup.objects.create(
            slot=slot, volunteer=self.coordinator_user, team=self.team
        )

        count = notify_event_updated(event, ["Time changed to 10:00 AM"])
        self.assertEqual(count, 2)

    def test_scheduled_blast_trigger(self):
        """Scheduled blast with send_at in the past gets triggered."""
        blast = create_blast(
            self.team,
            self.admin_user,
            status=BlastStatus.DRAFT,
            send_at=timezone.now() - timedelta(minutes=1),
        )
        create_recipient(blast, self.member_user)

        with patch("apps.notifications.tasks.send_blast.delay") as mock_delay:
            from apps.notifications.tasks import send_scheduled_blasts
            send_scheduled_blasts()
            mock_delay.assert_called_once_with(blast.pk)
