"""
Email notification backend using Django's built-in send_mail.
"""

import logging

from django.core.mail import send_mail
from django.conf import settings

from .base import NotificationBackend

logger = logging.getLogger(__name__)


class DjangoEmailBackend(NotificationBackend):
    """Sends email notifications via Django's email framework."""

    def send_email(self, recipient_email: str, subject: str, body_html: str, body_text: str) -> str:
        """Send an email using Django's send_mail."""
        send_mail(
            subject=subject,
            message=body_text,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient_email],
            html_message=body_html,
            fail_silently=False,
        )
        logger.info("Email sent to %s: %s", recipient_email, subject)
        return f"email-{recipient_email}"

    def send_sms(self, phone_number: str, body: str) -> str:
        """Email backend does not support SMS. Raises NotImplementedError."""
        raise NotImplementedError("DjangoEmailBackend does not support SMS. Use a dedicated SMS backend.")
