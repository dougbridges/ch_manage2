"""
Tests for the notifications REST API.
"""

from unittest.mock import patch

from rest_framework import status
from rest_framework.test import APIClient

from ..models import BlastStatus, NotificationChannel
from .base import NotificationTestBase, create_blast, create_recipient


class BlastAPITest(NotificationTestBase):
    def get_api_client(self, user):
        client = APIClient()
        client.login(username=user.email, password="testpass123")
        return client

    def test_list_blasts_as_admin(self):
        create_blast(self.team, self.admin_user, subject="Test")
        client = self.get_api_client(self.admin_user)
        url = f"/api/a/{self.team.slug}/notifications/blasts/"
        response = client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)

    def test_list_blasts_as_coordinator_forbidden(self):
        client = self.get_api_client(self.coordinator_user)
        url = f"/api/a/{self.team.slug}/notifications/blasts/"
        response = client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_blast_via_api(self):
        client = self.get_api_client(self.admin_user)
        url = f"/api/a/{self.team.slug}/notifications/blasts/"
        data = {
            "subject": "API Blast",
            "body": "Created via API.",
            "channel": NotificationChannel.EMAIL,
        }
        response = client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_retrieve_blast_detail(self):
        blast = create_blast(self.team, self.admin_user)
        create_recipient(blast, self.member_user)
        client = self.get_api_client(self.admin_user)
        url = f"/api/a/{self.team.slug}/notifications/blasts/{blast.pk}/"
        response = client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["recipients"]), 1)

    @patch("apps.notifications.tasks.send_blast.delay")
    def test_send_blast_via_api(self, mock_delay):
        blast = create_blast(self.team, self.admin_user)
        create_recipient(blast, self.member_user)
        client = self.get_api_client(self.admin_user)
        url = f"/api/a/{self.team.slug}/notifications/blasts/{blast.pk}/send/"
        response = client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        blast.refresh_from_db()
        self.assertEqual(blast.status, BlastStatus.SENDING)
        mock_delay.assert_called_once_with(blast.pk)

    @patch("apps.notifications.tasks.send_blast.delay")
    def test_cannot_send_already_sent(self, mock_delay):
        blast = create_blast(self.team, self.admin_user, status=BlastStatus.SENT)
        client = self.get_api_client(self.admin_user)
        url = f"/api/a/{self.team.slug}/notifications/blasts/{blast.pk}/send/"
        response = client.post(url)
        self.assertEqual(response.status_code, 400)
        mock_delay.assert_not_called()

    def test_member_cannot_access(self):
        client = self.get_api_client(self.member_user)
        url = f"/api/a/{self.team.slug}/notifications/blasts/"
        response = client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
