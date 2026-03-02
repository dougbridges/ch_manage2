"""
Tests for event list filtering and CSV exports (Phase 6B/6C).
"""

from django.utils import timezone

from ..models import EventCategory
from .base import EventTestBase, create_event, create_signup, create_slot


class EventFilterTest(EventTestBase):
    """Tests for the event list filtering feature."""

    def test_filter_by_category(self):
        create_event(self.team, self.admin_user, title="Worship Event", category=EventCategory.WORSHIP)
        create_event(self.team, self.admin_user, title="Youth Event", category=EventCategory.YOUTH)

        client = self.get_client(self.member_user)
        url = f"/a/{self.team.slug}/events/?category=worship"
        response = client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Worship Event")
        self.assertNotContains(response, "Youth Event")

    def test_filter_by_search(self):
        create_event(self.team, self.admin_user, title="VBS Week")
        create_event(self.team, self.admin_user, title="Potluck Night")

        client = self.get_client(self.member_user)
        url = f"/a/{self.team.slug}/events/?q=VBS"
        response = client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "VBS Week")
        self.assertNotContains(response, "Potluck Night")

    def test_filter_by_date_range(self):
        now = timezone.now()
        create_event(
            self.team, self.admin_user, title="Soon Event",
            start_datetime=now + timezone.timedelta(days=1),
            end_datetime=now + timezone.timedelta(days=1, hours=2),
        )
        create_event(
            self.team, self.admin_user, title="Far Event",
            start_datetime=now + timezone.timedelta(days=60),
            end_datetime=now + timezone.timedelta(days=60, hours=2),
        )

        date_from = (now + timezone.timedelta(days=50)).strftime("%Y-%m-%d")
        client = self.get_client(self.member_user)
        url = f"/a/{self.team.slug}/events/?date_from={date_from}"
        response = client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Far Event")
        self.assertNotContains(response, "Soon Event")

    def test_clear_filters_returns_all(self):
        create_event(self.team, self.admin_user, title="All Visible")
        client = self.get_client(self.member_user)
        url = f"/a/{self.team.slug}/events/"
        response = client.get(url)
        self.assertContains(response, "All Visible")


class EventExportTest(EventTestBase):
    """Tests for CSV export functionality."""

    def test_export_events_csv(self):
        create_event(self.team, self.admin_user, title="CSV Event")
        client = self.get_client(self.coordinator_user)
        url = f"/a/{self.team.slug}/events/export/"
        response = client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv")
        content = response.content.decode()
        self.assertIn("CSV Event", content)

    def test_export_event_signups_csv(self):
        event = create_event(self.team, self.admin_user)
        slot = create_slot(event)
        create_signup(slot, self.member_user)

        client = self.get_client(self.coordinator_user)
        url = f"/a/{self.team.slug}/events/{event.pk}/export-signups/"
        response = client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv")
        content = response.content.decode()
        self.assertIn("Ushers", content)

    def test_export_requires_coordinator(self):
        client = self.get_client(self.member_user)
        url = f"/a/{self.team.slug}/events/export/"
        response = client.get(url)
        self.assertIn(response.status_code, [302, 403])
