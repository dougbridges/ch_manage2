"""
Abstract base class for notification delivery backends.

All notification backends must implement send_email() and send_sms().
The backend is selected via settings NOTIFICATION_EMAIL_BACKEND and
NOTIFICATION_SMS_BACKEND.
"""

from abc import ABC, abstractmethod


class NotificationBackend(ABC):
    """Abstract base class for notification delivery backends."""

    @abstractmethod
    def send_email(self, recipient_email: str, subject: str, body_html: str, body_text: str) -> str:
        """
        Send an email notification.

        Args:
            recipient_email: The recipient's email address.
            subject: Email subject line.
            body_html: HTML body content.
            body_text: Plain text body content.

        Returns:
            An external message ID for tracking (e.g., email message-id).
        """
        ...

    @abstractmethod
    def send_sms(self, phone_number: str, body: str) -> str:
        """
        Send an SMS notification.

        Args:
            phone_number: The recipient's phone number in E.164 format.
            body: The SMS message body.

        Returns:
            An external message ID for tracking (e.g., Twilio SID).
        """
        ...
