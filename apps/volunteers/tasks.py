"""
Celery tasks for the volunteers app.

Handles shift reminder notifications and automatic rotation generation.
"""

import logging
from datetime import timedelta

from celery import shared_task
from django.template.loader import render_to_string
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task
def send_shift_reminders(days_ahead: int = 2):
    """
    Periodic task: send reminders for shifts happening in the next N days.

    Only sends for shifts in 'scheduled' or 'confirmed' status that
    haven't already received a reminder.
    """
    from apps.notifications.backends.loader import get_email_backend
    from apps.notifications.models import ContactPreference

    from .models import ScheduledShift, ShiftStatus

    cutoff = timezone.now().date() + timedelta(days=days_ahead)
    shifts = ScheduledShift.objects.filter(
        date__lte=cutoff,
        date__gte=timezone.now().date(),
        reminder_sent=False,
        status__in=[ShiftStatus.SCHEDULED, ShiftStatus.CONFIRMED],
    ).select_related("volunteer__user", "schedule", "event")

    backend = get_email_backend()
    sent_count = 0

    for shift in shifts:
        user = shift.volunteer.user
        try:
            body_html = render_to_string("volunteers/email/shift_reminder.html", {
                "shift": shift,
                "user": user,
            })
            body_text = render_to_string("volunteers/email/shift_reminder.txt", {
                "shift": shift,
                "user": user,
            })
            backend.send_email(
                recipient_email=user.email,
                subject=f"Shift Reminder: {shift.schedule.name} on {shift.date}",
                body_html=body_html,
                body_text=body_text,
            )
            shift.reminder_sent = True
            shift.save(update_fields=["reminder_sent"])
            sent_count += 1
        except Exception:
            logger.exception("Failed to send shift reminder to %s for shift %d", user.email, shift.pk)

    if sent_count:
        logger.info("Sent %d shift reminders", sent_count)


@shared_task
def auto_generate_rotations(weeks_ahead: int = 4):
    """
    Periodic task: auto-generate shifts for active rotation schedules.

    Generates shifts for the next N weeks if they don't already exist.
    Only processes schedules with round_robin or weighted strategy.
    """
    from datetime import date

    from .models import RotationSchedule
    from .rotation import generate_rotation

    today = timezone.now().date()
    end_date = today + timedelta(weeks=weeks_ahead)

    schedules = RotationSchedule.objects.filter(
        is_active=True,
        rotation_strategy__in=["round_robin", "weighted"],
    )

    total_shifts = 0
    for schedule in schedules:
        # Generate list of dates (e.g., weekly on the event's day of week)
        dates = _get_schedule_dates(schedule, today, end_date)
        if dates:
            shifts = generate_rotation(schedule, dates)
            total_shifts += len(shifts)

    if total_shifts:
        logger.info("Auto-generated %d shifts across %d schedules", total_shifts, schedules.count())


def _get_schedule_dates(schedule, start_date, end_date):
    """
    Determine which dates a rotation schedule needs shifts for.

    If linked to a recurring event, uses the event's recurrence pattern.
    Otherwise falls back to weekly on a default day.
    """
    from datetime import timedelta

    dates = []
    if schedule.event and schedule.event.recurrence:
        # Use the recurrence field to get occurrences
        try:
            occurrences = schedule.event.recurrence.between(start_date, end_date, dtstart=start_date)
            dates = [occ.date() if hasattr(occ, "date") else occ for occ in occurrences]
        except Exception:
            logger.exception("Failed to get recurrence dates for schedule %s", schedule.name)
    elif schedule.event and schedule.event.start_datetime:
        # Fall back to weekly on the event's day of week
        day_of_week = schedule.event.start_datetime.weekday()
        current = start_date
        while current <= end_date:
            if current.weekday() == day_of_week:
                dates.append(current)
            current += timedelta(days=1)

    return dates
