"""
Tests for notification models: MessageBlast, MessageRecipient, ContactPreference.
"""

from django.db import IntegrityError

from ..models import BlastStatus, NotificationChannel, RecipientStatus
from .base import NotificationTestBase, create_blast, create_preference, create_recipient


class MessageBlastModelTest(NotificationTestBase):
    """Tests for the MessageBlast model."""

    def test_create_blast(self):
        blast = create_blast(self.team, self.admin_user)
        self.assertEqual(blast.subject, "Test Blast")
        self.assertEqual(blast.status, BlastStatus.DRAFT)
        self.assertEqual(blast.team, self.team)
        self.assertEqual(blast.created_by, self.admin_user)

    def test_blast_str_with_subject(self):
        blast = create_blast(self.team, self.admin_user, subject="Important Update")
        self.assertEqual(str(blast), "Important Update")

    def test_blast_str_without_subject(self):
        blast = create_blast(self.team, self.admin_user, subject="")
        self.assertIn("Email blast", str(blast))

    def test_blast_ordering(self):
        blast1 = create_blast(self.team, self.admin_user, subject="First")
        blast2 = create_blast(self.team, self.admin_user, subject="Second")
        from ..models import MessageBlast
        blasts = list(MessageBlast.objects.filter(team=self.team))
        self.assertEqual(blasts[0], blast2)  # newest first
        self.assertEqual(blasts[1], blast1)

    def test_recipient_count(self):
        blast = create_blast(self.team, self.admin_user)
        create_recipient(blast, self.admin_user)
        create_recipient(blast, self.member_user)
        self.assertEqual(blast.recipient_count, 2)

    def test_sent_count(self):
        blast = create_blast(self.team, self.admin_user)
        create_recipient(blast, self.admin_user, status=RecipientStatus.SENT)
        create_recipient(blast, self.member_user, status=RecipientStatus.DELIVERED)
        create_recipient(blast, self.coordinator_user, status=RecipientStatus.PENDING)
        self.assertEqual(blast.sent_count, 2)

    def test_failed_count(self):
        blast = create_blast(self.team, self.admin_user)
        create_recipient(blast, self.admin_user, status=RecipientStatus.FAILED)
        create_recipient(blast, self.member_user, status=RecipientStatus.BOUNCED)
        create_recipient(blast, self.coordinator_user, status=RecipientStatus.SENT)
        self.assertEqual(blast.failed_count, 2)


class MessageRecipientModelTest(NotificationTestBase):
    """Tests for the MessageRecipient model."""

    def test_create_recipient(self):
        blast = create_blast(self.team, self.admin_user)
        recipient = create_recipient(blast, self.member_user)
        self.assertEqual(recipient.blast, blast)
        self.assertEqual(recipient.user, self.member_user)
        self.assertEqual(recipient.status, RecipientStatus.PENDING)

    def test_unique_together_blast_user_channel(self):
        blast = create_blast(self.team, self.admin_user)
        create_recipient(blast, self.member_user, channel=NotificationChannel.EMAIL)
        with self.assertRaises(IntegrityError):
            create_recipient(blast, self.member_user, channel=NotificationChannel.EMAIL)

    def test_same_user_different_channel_allowed(self):
        blast = create_blast(self.team, self.admin_user)
        create_recipient(blast, self.member_user, channel=NotificationChannel.EMAIL)
        recipient_sms = create_recipient(blast, self.member_user, channel=NotificationChannel.SMS)
        self.assertEqual(recipient_sms.channel, NotificationChannel.SMS)

    def test_cascade_delete_on_blast(self):
        blast = create_blast(self.team, self.admin_user)
        create_recipient(blast, self.member_user)
        blast_pk = blast.pk
        blast.delete()
        from ..models import MessageRecipient
        self.assertEqual(MessageRecipient.objects.filter(blast_id=blast_pk).count(), 0)


class ContactPreferenceModelTest(NotificationTestBase):
    """Tests for the ContactPreference model."""

    def test_create_preference(self):
        pref = create_preference(self.team, self.member_user)
        self.assertTrue(pref.receive_email)
        self.assertFalse(pref.receive_sms)

    def test_unique_together_team_user(self):
        create_preference(self.team, self.member_user)
        with self.assertRaises(IntegrityError):
            create_preference(self.team, self.member_user)

    def test_preference_str(self):
        pref = create_preference(self.team, self.member_user, receive_email=True, receive_sms=True)
        self.assertIn("email", str(pref))
        self.assertIn("sms", str(pref))

    def test_preference_str_no_channels(self):
        pref = create_preference(self.team, self.member_user, receive_email=False, receive_sms=False)
        self.assertIn("none", str(pref))
