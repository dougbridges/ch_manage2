"""
High-level notification helpers for the events app.

Sends event announcements, update notifications, and signup confirmations
using the notification backends configured in settings.
"""

import logging

from django.template.loader import render_to_string

from apps.notifications.backends.loader import get_email_backend
from apps.notifications.models import ContactPreference
from apps.teams.models import Membership

logger = logging.getLogger(__name__)


def notify_event_created(event):
    """
    Send an announcement to all team members about a new published event.

    Respects contact preferences — only sends to members who have receive_email enabled.
    """
    if not event.is_published:
        return

    backend = get_email_backend()
    memberships = Membership.objects.filter(team=event.team).select_related("user")
    sent_count = 0

    for membership in memberships:
        user = membership.user
        pref = ContactPreference.objects.filter(team=event.team, user=user).first()
        if pref and not pref.receive_email:
            continue

        try:
            body_html = render_to_string("events/email/event_announcement.html", {
                "event": event,
                "user": user,
            })
            body_text = render_to_string("events/email/event_announcement.txt", {
                "event": event,
                "user": user,
            })
            backend.send_email(
                recipient_email=user.email,
                subject=f"New Event: {event.title}",
                body_html=body_html,
                body_text=body_text,
            )
            sent_count += 1
        except Exception:
            logger.exception("Failed to send event announcement to %s", user.email)

    logger.info("Sent %d event announcements for '%s'", sent_count, event.title)
    return sent_count


def notify_event_updated(event, changes: list[str]):
    """
    Notify signed-up volunteers about changes to an event.

    Only notifies users who have active signups for this event's volunteer slots.
    The changes parameter is a list of human-readable change descriptions
    (e.g., ["Time changed to 10:00 AM", "Location changed to Fellowship Hall"]).
    """
    backend = get_email_backend()

    # Get unique volunteers signed up for this event
    from .models import VolunteerSignup
    signups = VolunteerSignup.objects.filter(
        slot__event=event,
    ).exclude(status="cancelled").select_related("volunteer")

    notified_users = set()
    sent_count = 0

    for signup in signups:
        user = signup.volunteer
        if user.pk in notified_users:
            continue
        notified_users.add(user.pk)

        try:
            body_html = render_to_string("events/email/event_updated.html", {
                "event": event,
                "user": user,
                "changes": changes,
            })
            body_text = render_to_string("events/email/event_updated.txt", {
                "event": event,
                "user": user,
                "changes": changes,
            })
            backend.send_email(
                recipient_email=user.email,
                subject=f"Event Updated: {event.title}",
                body_html=body_html,
                body_text=body_text,
            )
            sent_count += 1
        except Exception:
            logger.exception("Failed to send event update to %s", user.email)

    logger.info("Sent %d event update notifications for '%s'", sent_count, event.title)
    return sent_count


def notify_signup_confirmation(signup):
    """
    Send a confirmation email to a volunteer who just signed up for a slot.
    """
    backend = get_email_backend()
    user = signup.volunteer
    event = signup.slot.event

    try:
        body_html = render_to_string("events/email/signup_confirmation.html", {
            "signup": signup,
            "event": event,
            "user": user,
        })
        body_text = render_to_string("events/email/signup_confirmation.txt", {
            "signup": signup,
            "event": event,
            "user": user,
        })
        backend.send_email(
            recipient_email=user.email,
            subject=f"Signup Confirmed: {signup.slot.role_name} for {event.title}",
            body_html=body_html,
            body_text=body_text,
        )
        return True
    except Exception:
        logger.exception("Failed to send signup confirmation to %s", user.email)
        return False
