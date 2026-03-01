"""
Notification models for Planning Center Lite.

Defines MessageBlast (an email or SMS blast to team members),
MessageRecipient (delivery tracking per recipient), and
ContactPreference (user opt-in settings for email/SMS).
"""

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.teams.models import BaseTeamModel


class NotificationChannel(models.TextChoices):
    """Delivery channels for notifications."""

    EMAIL = "email", _("Email")
    SMS = "sms", _("SMS")


class BlastStatus(models.TextChoices):
    """Lifecycle status for a message blast."""

    DRAFT = "draft", _("Draft")
    SENDING = "sending", _("Sending")
    SENT = "sent", _("Sent")
    FAILED = "failed", _("Failed")


class RecipientStatus(models.TextChoices):
    """Delivery status for an individual recipient."""

    PENDING = "pending", _("Pending")
    SENT = "sent", _("Sent")
    DELIVERED = "delivered", _("Delivered")
    FAILED = "failed", _("Failed")
    BOUNCED = "bounced", _("Bounced")


class MessageBlast(BaseTeamModel):
    """
    A message blast (email or SMS) sent to team members.

    Blasts can be sent immediately or scheduled for a future time.
    Only admins can compose and send blasts.

    The recipient_filter JSONField stores targeting criteria:
    - {"all": true} — all team members
    - {"event_id": 5} — volunteers signed up for event 5
    """

    subject = models.CharField(_("subject"), max_length=200, blank=True)
    body = models.TextField(_("body"))
    channel = models.CharField(
        _("channel"),
        max_length=10,
        choices=NotificationChannel.choices,
        default=NotificationChannel.EMAIL,
    )
    status = models.CharField(
        _("status"),
        max_length=20,
        choices=BlastStatus.choices,
        default=BlastStatus.DRAFT,
    )
    send_at = models.DateTimeField(_("scheduled send time"), null=True, blank=True)
    sent_at = models.DateTimeField(_("actual send time"), null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("created by"),
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_blasts",
    )
    recipient_filter = models.JSONField(_("recipient filter"), default=dict)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("message blast")
        verbose_name_plural = _("message blasts")

    def __str__(self) -> str:
        if self.subject:
            return self.subject
        return f"{self.get_channel_display()} blast ({self.created_at:%Y-%m-%d})"

    @property
    def recipient_count(self) -> int:
        return self.recipients.count()

    @property
    def sent_count(self) -> int:
        return self.recipients.filter(status__in=[RecipientStatus.SENT, RecipientStatus.DELIVERED]).count()

    @property
    def failed_count(self) -> int:
        return self.recipients.filter(status__in=[RecipientStatus.FAILED, RecipientStatus.BOUNCED]).count()


class MessageRecipient(BaseTeamModel):
    """
    Tracks delivery status for each recipient of a blast.

    One record per user per blast per channel, allowing per-recipient
    retry and status tracking.
    """

    blast = models.ForeignKey(
        MessageBlast,
        verbose_name=_("blast"),
        on_delete=models.CASCADE,
        related_name="recipients",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("user"),
        on_delete=models.CASCADE,
        related_name="received_blasts",
    )
    channel = models.CharField(
        _("channel"),
        max_length=10,
        choices=NotificationChannel.choices,
    )
    status = models.CharField(
        _("status"),
        max_length=20,
        choices=RecipientStatus.choices,
        default=RecipientStatus.PENDING,
    )
    sent_at = models.DateTimeField(_("sent at"), null=True, blank=True)
    external_id = models.CharField(_("external ID"), max_length=200, blank=True)
    error_message = models.TextField(_("error message"), blank=True)

    class Meta:
        unique_together = ["blast", "user", "channel"]
        verbose_name = _("message recipient")
        verbose_name_plural = _("message recipients")

    def __str__(self) -> str:
        return f"{self.user} — {self.blast} ({self.get_status_display()})"


class ContactPreference(BaseTeamModel):
    """
    A team member's notification preferences.

    Each user has one preference record per team, controlling which
    channels they've opted in to and their phone number for SMS.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("user"),
        on_delete=models.CASCADE,
        related_name="contact_preferences",
    )
    phone_number = models.CharField(_("phone number"), max_length=20, blank=True)
    receive_email = models.BooleanField(_("receive email"), default=True)
    receive_sms = models.BooleanField(_("receive SMS"), default=False)

    class Meta:
        unique_together = ["team", "user"]
        verbose_name = _("contact preference")
        verbose_name_plural = _("contact preferences")

    def __str__(self) -> str:
        channels = []
        if self.receive_email:
            channels.append("email")
        if self.receive_sms:
            channels.append("sms")
        return f"{self.user} — {', '.join(channels) or 'none'}"
