"""
Tests for notification Celery tasks: send_blast, send_single_notification, send_scheduled_blasts.
"""

from unittest.mock import patch

from django.test import TestCase, override_settings
from django.utils import timezone

from ..models import BlastStatus, MessageBlast, NotificationChannel, RecipientStatus
from .base import (
    NotificationTestBase,
    create_blast,
    create_preference,
    create_recipient,
)


class SendBlastTaskTest(NotificationTestBase):
    """Tests for the send_blast task."""

    @patch("apps.notifications.tasks.send_single_notification.delay")
    def test_queues_recipients(self, mock_delay):
        blast = create_blast(self.team, self.admin_user)
        r1 = create_recipient(blast, self.member_user)
        r2 = create_recipient(blast, self.coordinator_user)

        from ..tasks import send_blast
        send_blast(blast.pk)

        self.assertEqual(mock_delay.call_count, 2)
        blast.refresh_from_db()
        self.assertEqual(blast.status, BlastStatus.SENT)
        self.assertIsNotNone(blast.sent_at)

    @patch("apps.notifications.tasks.send_single_notification.delay")
    def test_nonexistent_blast(self, mock_delay):
        from ..tasks import send_blast
        send_blast(99999)  # should not raise
        mock_delay.assert_not_called()


class SendSingleNotificationTaskTest(NotificationTestBase):
    """Tests for the send_single_notification task."""

    @override_settings(
        NOTIFICATION_EMAIL_BACKEND="apps.notifications.backends.console_backend.ConsoleBackend"
    )
    @patch("apps.notifications.tasks.send_single_notification.retry")
    def test_send_email_notification(self, mock_retry):
        blast = create_blast(self.team, self.admin_user, channel=NotificationChannel.EMAIL)
        recipient = create_recipient(blast, self.member_user)

        from ..tasks import send_single_notification
        send_single_notification(recipient.pk)

        recipient.refresh_from_db()
        self.assertEqual(recipient.status, RecipientStatus.SENT)
        self.assertIsNotNone(recipient.sent_at)
        self.assertEqual(recipient.external_id, "console")

    @override_settings(
        NOTIFICATION_SMS_BACKEND="apps.notifications.backends.console_backend.ConsoleBackend"
    )
    @patch("apps.notifications.tasks.send_single_notification.retry")
    def test_send_sms_notification(self, mock_retry):
        blast = create_blast(self.team, self.admin_user, channel=NotificationChannel.SMS)
        create_preference(self.team, self.member_user, receive_sms=True, phone_number="+15551234567")
        recipient = create_recipient(blast, self.member_user, channel=NotificationChannel.SMS)

        from ..tasks import send_single_notification
        send_single_notification(recipient.pk)

        recipient.refresh_from_db()
        self.assertEqual(recipient.status, RecipientStatus.SENT)

    @patch("apps.notifications.tasks.send_single_notification.retry")
    def test_sms_fails_without_phone(self, mock_retry):
        blast = create_blast(self.team, self.admin_user, channel=NotificationChannel.SMS)
        recipient = create_recipient(blast, self.member_user, channel=NotificationChannel.SMS)

        from ..tasks import send_single_notification
        send_single_notification(recipient.pk)

        recipient.refresh_from_db()
        self.assertEqual(recipient.status, RecipientStatus.FAILED)
        self.assertIn("No phone number", recipient.error_message)

    @patch("apps.notifications.tasks.send_single_notification.retry")
    def test_nonexistent_recipient(self, mock_retry):
        from ..tasks import send_single_notification
        send_single_notification(99999)  # should not raise
        mock_retry.assert_not_called()


class SendScheduledBlastsTaskTest(NotificationTestBase):
    """Tests for the send_scheduled_blasts periodic task."""

    @patch("apps.notifications.tasks.send_blast.delay")
    def test_triggers_due_blasts(self, mock_delay):
        blast = create_blast(
            self.team,
            self.admin_user,
            status=BlastStatus.DRAFT,
            send_at=timezone.now() - timezone.timedelta(minutes=1),
        )

        from ..tasks import send_scheduled_blasts
        send_scheduled_blasts()

        blast.refresh_from_db()
        self.assertEqual(blast.status, BlastStatus.SENDING)
        mock_delay.assert_called_once_with(blast.pk)

    @patch("apps.notifications.tasks.send_blast.delay")
    def test_ignores_future_blasts(self, mock_delay):
        blast = create_blast(
            self.team,
            self.admin_user,
            status=BlastStatus.DRAFT,
            send_at=timezone.now() + timezone.timedelta(hours=1),
        )

        from ..tasks import send_scheduled_blasts
        send_scheduled_blasts()

        blast.refresh_from_db()
        self.assertEqual(blast.status, BlastStatus.DRAFT)
        mock_delay.assert_not_called()

    @patch("apps.notifications.tasks.send_blast.delay")
    def test_ignores_already_sent(self, mock_delay):
        blast = create_blast(
            self.team,
            self.admin_user,
            status=BlastStatus.SENT,
            send_at=timezone.now() - timezone.timedelta(minutes=1),
        )

        from ..tasks import send_scheduled_blasts
        send_scheduled_blasts()

        mock_delay.assert_not_called()
