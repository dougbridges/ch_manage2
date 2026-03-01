"""
Twilio SMS notification backend.

Requires TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, and TWILIO_FROM_NUMBER in settings.
"""

import logging

from django.conf import settings

from .base import NotificationBackend

logger = logging.getLogger(__name__)


class TwilioBackend(NotificationBackend):
    """Sends SMS notifications via the Twilio REST API."""

    def __init__(self):
        # Lazy import to avoid requiring twilio in environments that don't use it
        from twilio.rest import Client

        self.client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        self.from_number = settings.TWILIO_FROM_NUMBER

    def send_email(self, recipient_email: str, subject: str, body_html: str, body_text: str) -> str:
        """Twilio backend does not support email. Raises NotImplementedError."""
        raise NotImplementedError("TwilioBackend does not support email. Use a dedicated email backend.")

    def send_sms(self, phone_number: str, body: str) -> str:
        """Send an SMS via Twilio."""
        message = self.client.messages.create(
            body=body,
            from_=self.from_number,
            to=phone_number,
        )
        logger.info("SMS sent to %s, SID: %s", phone_number, message.sid)
        return message.sid
