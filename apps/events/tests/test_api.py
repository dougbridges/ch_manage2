"""
Tests for the events REST API.
"""

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from .base import EventTestBase, create_event, create_slot, create_signup


class EventAPITest(EventTestBase):
    """Tests for the Event API viewset."""

    def get_api_client(self, user):
        client = APIClient()
        client.login(username=user.email, password="testpass123")
        return client

    def test_list_events(self):
        create_event(self.team, self.admin_user)
        client = self.get_api_client(self.member_user)
        url = f"/api/a/{self.team.slug}/events/"
        response = client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)

    def test_create_event_as_coordinator(self):
        client = self.get_api_client(self.coordinator_user)
        url = f"/api/a/{self.team.slug}/events/"
        data = {
            "title": "API Event",
            "description": "Created via API",
            "start_datetime": "2026-04-01T10:00:00Z",
            "end_datetime": "2026-04-01T12:00:00Z",
            "category": "worship",
        }
        response = client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_event_as_member_forbidden(self):
        client = self.get_api_client(self.member_user)
        url = f"/api/a/{self.team.slug}/events/"
        data = {
            "title": "Should Fail",
            "start_datetime": "2026-04-01T10:00:00Z",
            "end_datetime": "2026-04-01T12:00:00Z",
            "category": "other",
        }
        response = client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_event_as_admin(self):
        event = create_event(self.team, self.admin_user)
        client = self.get_api_client(self.admin_user)
        url = f"/api/a/{self.team.slug}/events/{event.pk}/"
        response = client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_delete_event_as_coordinator_forbidden(self):
        event = create_event(self.team, self.admin_user)
        client = self.get_api_client(self.coordinator_user)
        url = f"/api/a/{self.team.slug}/events/{event.pk}/"
        response = client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_retrieve_event_with_slots(self):
        event = create_event(self.team, self.admin_user)
        create_slot(event, role_name="Ushers")
        client = self.get_api_client(self.member_user)
        url = f"/api/a/{self.team.slug}/events/{event.pk}/"
        response = client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["volunteer_slots"]), 1)

    def test_non_member_denied(self):
        create_event(self.team, self.admin_user)
        client = self.get_api_client(self.non_member_user)
        url = f"/api/a/{self.team.slug}/events/"
        response = client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class SlotAPITest(EventTestBase):
    """Tests for the slot API viewset including signup/cancel."""

    def get_api_client(self, user):
        client = APIClient()
        client.login(username=user.email, password="testpass123")
        return client

    def test_list_slots(self):
        event = create_event(self.team, self.admin_user)
        create_slot(event)
        client = self.get_api_client(self.member_user)
        url = f"/api/a/{self.team.slug}/events/{event.pk}/slots/"
        response = client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_signup_via_api(self):
        event = create_event(self.team, self.admin_user)
        slot = create_slot(event)
        client = self.get_api_client(self.member_user)
        url = f"/api/a/{self.team.slug}/events/{event.pk}/slots/{slot.pk}/signup/"
        response = client.post(url)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_cancel_signup_via_api(self):
        event = create_event(self.team, self.admin_user)
        slot = create_slot(event)
        create_signup(slot, self.member_user)
        client = self.get_api_client(self.member_user)
        url = f"/api/a/{self.team.slug}/events/{event.pk}/slots/{slot.pk}/signup/"
        response = client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
