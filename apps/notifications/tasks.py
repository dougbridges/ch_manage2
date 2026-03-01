"""
Celery tasks for the notifications app.

Handles asynchronous sending of message blasts, per-recipient delivery,
and scheduled blast processing.
"""

import logging

from celery import shared_task
from django.template.loader import render_to_string
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task
def send_blast(blast_id: int):
    """
    Process and send all recipients for a message blast.

    Updates blast status to 'sent' or 'failed' when complete.
    Delegates per-recipient sending to send_single_notification for retry isolation.
    """
    from .models import BlastStatus, MessageBlast, RecipientStatus

    try:
        blast = MessageBlast.objects.get(pk=blast_id)
    except MessageBlast.DoesNotExist:
        logger.error("Blast %d not found", blast_id)
        return

    pending_recipients = blast.recipients.filter(status=RecipientStatus.PENDING)
    for recipient in pending_recipients:
        send_single_notification.delay(recipient.pk)

    blast.sent_at = timezone.now()
    blast.status = BlastStatus.SENT
    blast.save()
    logger.info("Blast %d queued %d recipients for delivery", blast_id, pending_recipients.count())


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_single_notification(self, recipient_id: int):
    """
    Send a single notification to one recipient.

    Called per-recipient for retry isolation — if one delivery fails,
    it doesn't block the others.
    """
    from .backends.loader import get_email_backend, get_sms_backend
    from .models import MessageRecipient, NotificationChannel, RecipientStatus

    try:
        recipient = MessageRecipient.objects.select_related("blast", "user").get(pk=recipient_id)
    except MessageRecipient.DoesNotExist:
        logger.error("Recipient %d not found", recipient_id)
        return

    blast = recipient.blast
    user = recipient.user

    try:
        if recipient.channel == NotificationChannel.EMAIL:
            backend = get_email_backend()
            body_html = render_to_string("notifications/email/blast.html", {"blast": blast, "user": user})
            body_text = render_to_string("notifications/email/blast.txt", {"blast": blast, "user": user})
            external_id = backend.send_email(
                recipient_email=user.email,
                subject=blast.subject,
                body_html=body_html,
                body_text=body_text,
            )
        elif recipient.channel == NotificationChannel.SMS:
            from .models import ContactPreference
            pref = ContactPreference.objects.filter(team=blast.team, user=user).first()
            if not pref or not pref.phone_number:
                recipient.status = RecipientStatus.FAILED
                recipient.error_message = "No phone number on file"
                recipient.save()
                return
            backend = get_sms_backend()
            body = render_to_string("notifications/sms/blast.txt", {"blast": blast, "user": user})
            external_id = backend.send_sms(phone_number=pref.phone_number, body=body)
        else:
            recipient.status = RecipientStatus.FAILED
            recipient.error_message = f"Unknown channel: {recipient.channel}"
            recipient.save()
            return

        recipient.status = RecipientStatus.SENT
        recipient.external_id = external_id
        recipient.sent_at = timezone.now()
        recipient.save()
        logger.info("Notification sent to %s via %s", user, recipient.channel)

    except Exception as exc:
        logger.exception("Failed to send notification to %s: %s", user, exc)
        recipient.status = RecipientStatus.FAILED
        recipient.error_message = str(exc)[:500]
        recipient.save()
        # Retry on transient failures
        raise self.retry(exc=exc)


@shared_task
def send_scheduled_blasts():
    """
    Periodic task: find blasts with send_at <= now and status=draft, trigger send.

    Runs every 5 minutes via django-celery-beat.
    """
    from .models import BlastStatus, MessageBlast

    now = timezone.now()
    scheduled = MessageBlast.objects.filter(
        status=BlastStatus.DRAFT,
        send_at__isnull=False,
        send_at__lte=now,
    )
    count = 0
    for blast in scheduled:
        blast.status = BlastStatus.SENDING
        blast.save()
        send_blast.delay(blast.pk)
        count += 1

    if count:
        logger.info("Triggered %d scheduled blasts", count)
