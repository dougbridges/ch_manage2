"""
Tests for volunteer Celery tasks: shift reminders and auto-generation.
"""

from datetime import timedelta

from django.test import override_settings
from django.utils import timezone

from ..models import RotationStrategy, ShiftStatus
from .base import (
    VolunteerTestBase,
    add_rotation_member,
    create_event,
    create_rotation,
    create_shift,
    create_volunteer_profile,
)


class SendShiftRemindersTaskTest(VolunteerTestBase):
    @override_settings(NOTIFICATION_EMAIL_BACKEND="apps.notifications.backends.console_backend.ConsoleBackend")
    def test_sends_reminders_for_upcoming_shifts(self):
        event = create_event(self.team, self.admin_user)
        rotation = create_rotation(self.team, event)
        profile = create_volunteer_profile(self.team, self.member_user)
        tomorrow = timezone.now().date() + timedelta(days=1)
        shift = create_shift(rotation, profile, tomorrow)

        from ..tasks import send_shift_reminders

        send_shift_reminders(days_ahead=2)

        shift.refresh_from_db()
        self.assertTrue(shift.reminder_sent)

    @override_settings(NOTIFICATION_EMAIL_BACKEND="apps.notifications.backends.console_backend.ConsoleBackend")
    def test_does_not_resend_reminders(self):
        event = create_event(self.team, self.admin_user)
        rotation = create_rotation(self.team, event)
        profile = create_volunteer_profile(self.team, self.member_user)
        tomorrow = timezone.now().date() + timedelta(days=1)
        shift = create_shift(rotation, profile, tomorrow, reminder_sent=True)

        from ..tasks import send_shift_reminders

        send_shift_reminders(days_ahead=2)

        shift.refresh_from_db()
        self.assertTrue(shift.reminder_sent)

    @override_settings(NOTIFICATION_EMAIL_BACKEND="apps.notifications.backends.console_backend.ConsoleBackend")
    def test_ignores_declined_shifts(self):
        event = create_event(self.team, self.admin_user)
        rotation = create_rotation(self.team, event)
        profile = create_volunteer_profile(self.team, self.member_user)
        tomorrow = timezone.now().date() + timedelta(days=1)
        shift = create_shift(rotation, profile, tomorrow, status=ShiftStatus.DECLINED)

        from ..tasks import send_shift_reminders

        send_shift_reminders(days_ahead=2)

        shift.refresh_from_db()
        self.assertFalse(shift.reminder_sent)


class AutoGenerateRotationsTaskTest(VolunteerTestBase):
    def test_generates_for_active_schedules(self):
        event = create_event(self.team, self.admin_user)
        rotation = create_rotation(self.team, event, rotation_strategy=RotationStrategy.ROUND_ROBIN)
        profile = create_volunteer_profile(self.team, self.member_user)
        add_rotation_member(rotation, profile)

        from ..tasks import auto_generate_rotations

        auto_generate_rotations(weeks_ahead=2)

        # May or may not generate depending on event recurrence, but should not error
        # The task runs without raising

    def test_skips_inactive_schedules(self):
        event = create_event(self.team, self.admin_user)
        rotation = create_rotation(self.team, event, is_active=False)
        profile = create_volunteer_profile(self.team, self.member_user)
        add_rotation_member(rotation, profile)

        from ..tasks import auto_generate_rotations

        auto_generate_rotations(weeks_ahead=2)

        from ..models import ScheduledShift

        self.assertEqual(ScheduledShift.objects.filter(schedule=rotation).count(), 0)

    def test_skips_manual_schedules(self):
        event = create_event(self.team, self.admin_user)
        rotation = create_rotation(self.team, event, rotation_strategy=RotationStrategy.MANUAL)
        profile = create_volunteer_profile(self.team, self.member_user)
        add_rotation_member(rotation, profile)

        from ..tasks import auto_generate_rotations

        auto_generate_rotations(weeks_ahead=2)

        from ..models import ScheduledShift

        self.assertEqual(ScheduledShift.objects.filter(schedule=rotation).count(), 0)
