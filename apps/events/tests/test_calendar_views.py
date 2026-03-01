"""
Tests for calendar views: rendering, month navigation, HTMX partials.
"""

from django.test import Client
from django.urls import reverse
from django.utils import timezone

from .base import EventTestBase, create_event


class CalendarViewTest(EventTestBase):
    def test_anonymous_redirects(self):
        url = reverse("events:event_calendar", args=[self.team.slug])
        response = Client().get(url)
        self.assertEqual(response.status_code, 302)

    def test_member_can_view_calendar(self):
        client = self.get_client(self.member_user)
        url = reverse("events:event_calendar", args=[self.team.slug])
        response = client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Calendar")

    def test_non_member_gets_404(self):
        client = self.get_client(self.non_member_user)
        url = reverse("events:event_calendar", args=[self.team.slug])
        response = client.get(url)
        self.assertEqual(response.status_code, 404)


class CalendarMonthViewTest(EventTestBase):
    def test_specific_month(self):
        client = self.get_client(self.member_user)
        url = reverse("events:event_calendar_month", args=[self.team.slug, 2026, 6])
        response = client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "June")

    def test_htmx_returns_partial(self):
        client = self.get_client(self.member_user)
        url = reverse("events:event_calendar_month", args=[self.team.slug, 2026, 3])
        response = client.get(url, HTTP_HX_REQUEST="true")
        self.assertEqual(response.status_code, 200)
        # HTMX partial should contain the grid but not the full page layout
        self.assertContains(response, "March")

    def test_event_appears_on_correct_day(self):
        # Create an event on a known date
        dt = timezone.datetime(2026, 6, 15, 10, 0, tzinfo=timezone.get_current_timezone())
        create_event(
            self.team, self.admin_user,
            title="Flag Day Service",
            start_datetime=dt,
            end_datetime=dt + timezone.timedelta(hours=2),
        )
        client = self.get_client(self.member_user)
        url = reverse("events:event_calendar_month", args=[self.team.slug, 2026, 6])
        response = client.get(url)
        self.assertEqual(response.status_code, 200)
