"""
Tests for notification views: blast list, compose, detail, send, and preferences.
"""

from unittest.mock import patch

from django.urls import reverse

from ..models import BlastStatus, MessageBlast, NotificationChannel
from .base import NotificationTestBase, create_blast, create_preference, create_recipient


class BlastListViewTest(NotificationTestBase):
    """Tests for the blast_list view."""

    def test_coordinator_can_view(self):
        client = self.get_client(self.coordinator_user)
        url = reverse("notifications:blast_list", args=[self.team.slug])
        response = client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_admin_can_view(self):
        client = self.get_client(self.admin_user)
        url = reverse("notifications:blast_list", args=[self.team.slug])
        response = client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_member_cannot_view(self):
        client = self.get_client(self.member_user)
        url = reverse("notifications:blast_list", args=[self.team.slug])
        response = client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_anonymous_redirected(self):
        url = reverse("notifications:blast_list", args=[self.team.slug])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)

    def test_blasts_listed(self):
        blast = create_blast(self.team, self.admin_user, subject="Church Picnic")
        client = self.get_client(self.admin_user)
        url = reverse("notifications:blast_list", args=[self.team.slug])
        response = client.get(url)
        self.assertContains(response, "Church Picnic")


class BlastComposeViewTest(NotificationTestBase):
    """Tests for the blast_compose view."""

    def test_admin_can_access(self):
        client = self.get_client(self.admin_user)
        url = reverse("notifications:blast_compose", args=[self.team.slug])
        response = client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_coordinator_cannot_compose(self):
        client = self.get_client(self.coordinator_user)
        url = reverse("notifications:blast_compose", args=[self.team.slug])
        response = client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_create_email_blast(self):
        create_preference(self.team, self.admin_user)
        create_preference(self.team, self.member_user)
        client = self.get_client(self.admin_user)
        url = reverse("notifications:blast_compose", args=[self.team.slug])
        data = {
            "subject": "Weekly Update",
            "body": "Here is what happened this week.",
            "channel": NotificationChannel.EMAIL,
        }
        response = client.post(url, data)
        self.assertEqual(response.status_code, 302)
        blast = MessageBlast.objects.filter(team=self.team, subject="Weekly Update").first()
        self.assertIsNotNone(blast)
        self.assertEqual(blast.created_by, self.admin_user)
        self.assertTrue(blast.recipients.exists())

    def test_email_blast_requires_subject(self):
        client = self.get_client(self.admin_user)
        url = reverse("notifications:blast_compose", args=[self.team.slug])
        data = {
            "subject": "",
            "body": "Some body text.",
            "channel": NotificationChannel.EMAIL,
        }
        response = client.post(url, data)
        self.assertEqual(response.status_code, 200)  # form re-rendered with errors

    def test_sms_blast_without_subject(self):
        create_preference(self.team, self.member_user, receive_sms=True, phone_number="+15551234567")
        client = self.get_client(self.admin_user)
        url = reverse("notifications:blast_compose", args=[self.team.slug])
        data = {
            "subject": "",
            "body": "Quick SMS update.",
            "channel": NotificationChannel.SMS,
        }
        response = client.post(url, data)
        self.assertEqual(response.status_code, 302)

    def test_sms_blast_skips_users_without_phone(self):
        # Member with SMS enabled but no phone number should be skipped
        create_preference(self.team, self.member_user, receive_sms=True, phone_number="")
        create_preference(self.team, self.coordinator_user, receive_sms=True, phone_number="+15559876543")
        client = self.get_client(self.admin_user)
        url = reverse("notifications:blast_compose", args=[self.team.slug])
        data = {
            "subject": "",
            "body": "SMS for phone owners only.",
            "channel": NotificationChannel.SMS,
        }
        response = client.post(url, data)
        self.assertEqual(response.status_code, 302)
        blast = MessageBlast.objects.filter(team=self.team, body="SMS for phone owners only.").first()
        # Only coordinator has a valid phone, so only 1 recipient
        self.assertEqual(blast.recipient_count, 1)


class BlastDetailViewTest(NotificationTestBase):
    """Tests for the blast_detail view."""

    def test_coordinator_can_view(self):
        blast = create_blast(self.team, self.admin_user)
        client = self.get_client(self.coordinator_user)
        url = reverse("notifications:blast_detail", args=[self.team.slug, blast.pk])
        response = client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_member_cannot_view(self):
        blast = create_blast(self.team, self.admin_user)
        client = self.get_client(self.member_user)
        url = reverse("notifications:blast_detail", args=[self.team.slug, blast.pk])
        response = client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_detail_shows_stats(self):
        blast = create_blast(self.team, self.admin_user, subject="Detail Test")
        create_recipient(blast, self.member_user)
        client = self.get_client(self.admin_user)
        url = reverse("notifications:blast_detail", args=[self.team.slug, blast.pk])
        response = client.get(url)
        self.assertContains(response, "Detail Test")


class BlastSendViewTest(NotificationTestBase):
    """Tests for the blast_send view."""

    @patch("apps.notifications.tasks.send_blast.delay")
    def test_admin_can_trigger_send(self, mock_delay):
        blast = create_blast(self.team, self.admin_user)
        create_recipient(blast, self.member_user)
        client = self.get_client(self.admin_user)
        url = reverse("notifications:blast_send", args=[self.team.slug, blast.pk])
        response = client.post(url)
        self.assertEqual(response.status_code, 302)
        blast.refresh_from_db()
        self.assertEqual(blast.status, BlastStatus.SENDING)
        mock_delay.assert_called_once_with(blast.pk)

    def test_coordinator_cannot_send(self):
        blast = create_blast(self.team, self.admin_user)
        client = self.get_client(self.coordinator_user)
        url = reverse("notifications:blast_send", args=[self.team.slug, blast.pk])
        response = client.post(url)
        self.assertEqual(response.status_code, 404)

    def test_cannot_send_already_sent(self):
        blast = create_blast(self.team, self.admin_user, status=BlastStatus.SENT)
        client = self.get_client(self.admin_user)
        url = reverse("notifications:blast_send", args=[self.team.slug, blast.pk])
        response = client.post(url)
        self.assertEqual(response.status_code, 302)
        blast.refresh_from_db()
        self.assertEqual(blast.status, BlastStatus.SENT)  # unchanged


class ContactPreferencesViewTest(NotificationTestBase):
    """Tests for the contact_preferences view."""

    def test_member_can_access(self):
        client = self.get_client(self.member_user)
        url = reverse("notifications:contact_preferences", args=[self.team.slug])
        response = client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_creates_preference_on_first_visit(self):
        from ..models import ContactPreference

        client = self.get_client(self.member_user)
        url = reverse("notifications:contact_preferences", args=[self.team.slug])
        client.get(url)
        self.assertTrue(ContactPreference.objects.filter(team=self.team, user=self.member_user).exists())

    def test_save_preferences(self):
        client = self.get_client(self.member_user)
        url = reverse("notifications:contact_preferences", args=[self.team.slug])
        data = {
            "receive_email": True,
            "receive_sms": True,
            "phone_number": "+15551234567",
        }
        response = client.post(url, data)
        self.assertEqual(response.status_code, 302)
        from ..models import ContactPreference

        pref = ContactPreference.objects.get(team=self.team, user=self.member_user)
        self.assertTrue(pref.receive_sms)
        self.assertEqual(pref.phone_number, "+15551234567")

    def test_sms_requires_phone(self):
        client = self.get_client(self.member_user)
        url = reverse("notifications:contact_preferences", args=[self.team.slug])
        data = {
            "receive_email": True,
            "receive_sms": True,
            "phone_number": "",
        }
        response = client.post(url, data)
        self.assertEqual(response.status_code, 200)  # form re-rendered with errors

    def test_anonymous_redirected(self):
        url = reverse("notifications:contact_preferences", args=[self.team.slug])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
