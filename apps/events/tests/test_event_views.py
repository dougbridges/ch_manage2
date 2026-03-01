"""
Tests for event CRUD views: permissions, form submission, redirects.
"""

from django.test import Client
from django.urls import reverse
from django.utils import timezone

from ..models import Event
from .base import EventTestBase, create_event


class EventListViewTest(EventTestBase):
    def test_anonymous_redirects_to_login(self):
        url = reverse("events:event_list", args=[self.team.slug])
        response = Client().get(url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("login", response.url)

    def test_member_can_view_list(self):
        create_event(self.team, self.admin_user)
        client = self.get_client(self.member_user)
        url = reverse("events:event_list", args=[self.team.slug])
        response = client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Sunday Worship")

    def test_non_member_gets_404(self):
        client = self.get_client(self.non_member_user)
        url = reverse("events:event_list", args=[self.team.slug])
        response = client.get(url)
        self.assertEqual(response.status_code, 404)


class EventDetailViewTest(EventTestBase):
    def test_member_can_view_detail(self):
        event = create_event(self.team, self.admin_user)
        client = self.get_client(self.member_user)
        url = reverse("events:event_detail", args=[self.team.slug, event.pk])
        response = client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, event.title)

    def test_unpublished_hidden_from_member(self):
        event = create_event(self.team, self.admin_user, is_published=False)
        client = self.get_client(self.member_user)
        url = reverse("events:event_detail", args=[self.team.slug, event.pk])
        response = client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_unpublished_visible_to_coordinator(self):
        event = create_event(self.team, self.admin_user, is_published=False)
        client = self.get_client(self.coordinator_user)
        url = reverse("events:event_detail", args=[self.team.slug, event.pk])
        response = client.get(url)
        self.assertEqual(response.status_code, 200)


class EventCreateViewTest(EventTestBase):
    def test_member_cannot_create(self):
        client = self.get_client(self.member_user)
        url = reverse("events:event_create", args=[self.team.slug])
        response = client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_coordinator_can_create(self):
        client = self.get_client(self.coordinator_user)
        url = reverse("events:event_create", args=[self.team.slug])
        response = client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_admin_can_create(self):
        client = self.get_client(self.admin_user)
        url = reverse("events:event_create", args=[self.team.slug])
        response = client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_create_event_post(self):
        client = self.get_client(self.coordinator_user)
        url = reverse("events:event_create", args=[self.team.slug])
        start = timezone.now() + timezone.timedelta(days=3)
        end = start + timezone.timedelta(hours=2)
        data = {
            "title": "Youth Night",
            "description": "Fun for teens",
            "location": "Youth Room",
            "start_datetime": start.strftime("%Y-%m-%dT%H:%M"),
            "end_datetime": end.strftime("%Y-%m-%dT%H:%M"),
            "category": "youth",
            "is_published": True,
        }
        response = client.post(url, data)
        self.assertEqual(response.status_code, 302)
        event = Event.objects.get(title="Youth Night")
        self.assertEqual(event.team, self.team)
        self.assertEqual(event.created_by, self.coordinator_user)

    def test_create_event_invalid_dates(self):
        """End date before start date should fail."""
        client = self.get_client(self.coordinator_user)
        url = reverse("events:event_create", args=[self.team.slug])
        start = timezone.now() + timezone.timedelta(days=3)
        end = start - timezone.timedelta(hours=1)  # end before start
        data = {
            "title": "Bad Event",
            "start_datetime": start.strftime("%Y-%m-%dT%H:%M"),
            "end_datetime": end.strftime("%Y-%m-%dT%H:%M"),
            "category": "other",
        }
        response = client.post(url, data)
        self.assertEqual(response.status_code, 200)  # re-renders form with errors
        self.assertFalse(Event.objects.filter(title="Bad Event").exists())


class EventEditViewTest(EventTestBase):
    def test_member_cannot_edit(self):
        event = create_event(self.team, self.admin_user)
        client = self.get_client(self.member_user)
        url = reverse("events:event_edit", args=[self.team.slug, event.pk])
        response = client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_coordinator_can_edit(self):
        event = create_event(self.team, self.admin_user)
        client = self.get_client(self.coordinator_user)
        url = reverse("events:event_edit", args=[self.team.slug, event.pk])
        response = client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_edit_event_post(self):
        event = create_event(self.team, self.admin_user)
        client = self.get_client(self.coordinator_user)
        url = reverse("events:event_edit", args=[self.team.slug, event.pk])
        start = timezone.now() + timezone.timedelta(days=5)
        end = start + timezone.timedelta(hours=3)
        data = {
            "title": "Updated Title",
            "start_datetime": start.strftime("%Y-%m-%dT%H:%M"),
            "end_datetime": end.strftime("%Y-%m-%dT%H:%M"),
            "category": "fellowship",
            "is_published": True,
        }
        response = client.post(url, data)
        self.assertEqual(response.status_code, 302)
        event.refresh_from_db()
        self.assertEqual(event.title, "Updated Title")


class EventDeleteViewTest(EventTestBase):
    def test_member_cannot_delete(self):
        event = create_event(self.team, self.admin_user)
        client = self.get_client(self.member_user)
        url = reverse("events:event_delete", args=[self.team.slug, event.pk])
        response = client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_coordinator_cannot_delete(self):
        event = create_event(self.team, self.admin_user)
        client = self.get_client(self.coordinator_user)
        url = reverse("events:event_delete", args=[self.team.slug, event.pk])
        response = client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_admin_can_delete(self):
        event = create_event(self.team, self.admin_user)
        client = self.get_client(self.admin_user)
        url = reverse("events:event_delete", args=[self.team.slug, event.pk])
        response = client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_delete_event_post(self):
        event = create_event(self.team, self.admin_user)
        pk = event.pk
        client = self.get_client(self.admin_user)
        url = reverse("events:event_delete", args=[self.team.slug, event.pk])
        response = client.post(url)
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Event.objects.filter(pk=pk).exists())
