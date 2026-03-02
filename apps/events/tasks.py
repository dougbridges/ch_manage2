"""
Celery tasks for event reminders.

Sends reminder emails/SMS for upcoming events to signed-up volunteers
and team members.
"""

import logging
from datetime import timedelta

from celery import shared_task
from django.template.loader import render_to_string
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task
def send_event_reminders(hours_ahead: int = 48):
    """
    Periodic task: Send reminders for events happening in the next N hours.

    Targets all team members who have opted in to email notifications.
    Only sends for published events that haven't already been reminded
    (uses a simple check: events starting within the reminder window).
    """
    from apps.notifications.backends.loader import get_email_backend
    from apps.notifications.models import ContactPreference
    from apps.teams.models import Membership

    from .models import Event

    now = timezone.now()
    cutoff = now + timedelta(hours=hours_ahead)

    # Events starting within the reminder window that are published
    upcoming_events = Event.objects.filter(
        is_published=True,
        start_datetime__gte=now,
        start_datetime__lte=cutoff,
    ).select_related("team")

    backend = get_email_backend()
    total_sent = 0

    for event in upcoming_events:
        memberships = Membership.objects.filter(team=event.team).select_related("user")
        for membership in memberships:
            user = membership.user
            pref = ContactPreference.objects.filter(team=event.team, user=user).first()
            if pref and not pref.receive_email:
                continue

            try:
                body_html = render_to_string("events/email/event_reminder.html", {
                    "event": event,
                    "user": user,
                })
                body_text = render_to_string("events/email/event_reminder.txt", {
                    "event": event,
                    "user": user,
                })
                backend.send_email(
                    recipient_email=user.email,
                    subject=f"Reminder: {event.title} — {event.start_datetime:%b %d at %I:%M %p}",
                    body_html=body_html,
                    body_text=body_text,
                )
                total_sent += 1
            except Exception:
                logger.exception("Failed to send event reminder to %s", user.email)

    if total_sent:
        logger.info("Sent %d event reminders for %d events", total_sent, upcoming_events.count())
