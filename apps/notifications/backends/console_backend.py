"""
Console notification backend for development and testing.

Logs all notifications to the console/logger instead of actually sending them.
"""

import logging

from .base import NotificationBackend

logger = logging.getLogger(__name__)


class ConsoleBackend(NotificationBackend):
    """Logs notifications to the console. Used for development and testing."""

    def send_email(self, recipient_email: str, subject: str, body_html: str, body_text: str) -> str:
        """Log email to console."""
        logger.info(
            "[ConsoleBackend] EMAIL to=%s subject='%s'\n%s",
            recipient_email, subject, body_text[:200],
        )
        return f"console-email-{recipient_email}"

    def send_sms(self, phone_number: str, body: str) -> str:
        """Log SMS to console."""
        logger.info(
            "[ConsoleBackend] SMS to=%s body='%s'",
            phone_number, body[:160],
        )
        return f"console-sms-{phone_number}"
