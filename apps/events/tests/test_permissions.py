"""
Tests for role-based access control on event views.

Verifies that admin, coordinator, member, and anonymous users have
the correct access levels to each view.
"""

from django.test import Client
from django.urls import reverse

from apps.teams.roles import ROLE_ADMIN, ROLE_COORDINATOR, ROLE_MEMBER, is_coordinator

from .base import EventTestBase, create_event, create_slot


class RolePermissionTest(EventTestBase):
    """Test the new coordinator role and is_coordinator function."""

    def test_admin_is_coordinator(self):
        self.assertTrue(is_coordinator(self.admin_user, self.team))

    def test_coordinator_is_coordinator(self):
        self.assertTrue(is_coordinator(self.coordinator_user, self.team))

    def test_member_is_not_coordinator(self):
        self.assertFalse(is_coordinator(self.member_user, self.team))

    def test_anonymous_is_not_coordinator(self):
        from django.contrib.auth.models import AnonymousUser
        self.assertFalse(is_coordinator(AnonymousUser(), self.team))


class EventViewPermissionMatrix(EventTestBase):
    """
    Permission matrix: test that each role can/cannot access each view.
    """

    def _assert_access(self, user, url, expected_status):
        client = self.get_client(user)
        response = client.get(url)
        self.assertEqual(
            response.status_code, expected_status,
            f"{user.email} expected {expected_status} at {url}, got {response.status_code}",
        )

    def test_event_list_access(self):
        url = reverse("events:event_list", args=[self.team.slug])
        self._assert_access(self.admin_user, url, 200)
        self._assert_access(self.coordinator_user, url, 200)
        self._assert_access(self.member_user, url, 200)
        self._assert_access(self.non_member_user, url, 404)

    def test_event_create_access(self):
        url = reverse("events:event_create", args=[self.team.slug])
        self._assert_access(self.admin_user, url, 200)
        self._assert_access(self.coordinator_user, url, 200)
        self._assert_access(self.member_user, url, 404)
        self._assert_access(self.non_member_user, url, 404)

    def test_event_edit_access(self):
        event = create_event(self.team, self.admin_user)
        url = reverse("events:event_edit", args=[self.team.slug, event.pk])
        self._assert_access(self.admin_user, url, 200)
        self._assert_access(self.coordinator_user, url, 200)
        self._assert_access(self.member_user, url, 404)

    def test_event_delete_access(self):
        event = create_event(self.team, self.admin_user)
        url = reverse("events:event_delete", args=[self.team.slug, event.pk])
        self._assert_access(self.admin_user, url, 200)
        self._assert_access(self.coordinator_user, url, 404)  # coordinator cannot delete
        self._assert_access(self.member_user, url, 404)

    def test_slot_create_access(self):
        event = create_event(self.team, self.admin_user)
        url = reverse("events:slot_create", args=[self.team.slug, event.pk])
        self._assert_access(self.admin_user, url, 200)
        self._assert_access(self.coordinator_user, url, 200)
        self._assert_access(self.member_user, url, 404)

    def test_anonymous_redirects(self):
        """All views should redirect anonymous users to login."""
        event = create_event(self.team, self.admin_user)
        slot = create_slot(event)
        urls = [
            reverse("events:event_list", args=[self.team.slug]),
            reverse("events:event_create", args=[self.team.slug]),
            reverse("events:event_detail", args=[self.team.slug, event.pk]),
            reverse("events:event_edit", args=[self.team.slug, event.pk]),
            reverse("events:event_delete", args=[self.team.slug, event.pk]),
            reverse("events:event_calendar", args=[self.team.slug]),
            reverse("events:slot_create", args=[self.team.slug, event.pk]),
        ]
        anon_client = Client()
        for url in urls:
            response = anon_client.get(url)
            self.assertEqual(
                response.status_code, 302,
                f"Anonymous should be redirected from {url}",
            )
            self.assertIn("login", response.url)
