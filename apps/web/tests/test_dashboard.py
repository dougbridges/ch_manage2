"""
Tests for the church dashboard (Phase 6A).

Verifies that the dashboard shows upcoming events, shifts, recent blasts,
stats, and quick actions for logged-in team members.
"""

from datetime import timedelta

from django.test import Client, TestCase, override_settings
from django.utils import timezone

from apps.events.models import Event, EventCategory
from apps.notifications.models import BlastStatus, MessageBlast, NotificationChannel
from apps.teams.models import Membership, Team
from apps.teams.roles import ROLE_ADMIN, ROLE_MEMBER
from apps.users.models import CustomUser
from apps.volunteers.models import ScheduledShift, RotationSchedule, VolunteerProfile

TEST_STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}


@override_settings(STORAGES=TEST_STORAGES)
class DashboardTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.team = Team.objects.create(name="Dashboard Church", slug="dashboard-church")
        cls.admin = CustomUser.objects.create_user(username="dash-admin@church.com", email="dash-admin@church.com", password="testpass123")
        cls.member = CustomUser.objects.create_user(username="dash-member@church.com", email="dash-member@church.com", password="testpass123")
        Membership.objects.create(team=cls.team, user=cls.admin, role=ROLE_ADMIN)
        Membership.objects.create(team=cls.team, user=cls.member, role=ROLE_MEMBER)

    def get_client(self, user):
        client = Client()
        client.login(username=user.email, password="testpass123")
        return client

    def test_dashboard_renders_for_member(self):
        client = self.get_client(self.member)
        url = f"/a/{self.team.slug}/"
        response = client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Upcoming Events")
        self.assertContains(response, "Quick Actions")

    def test_dashboard_shows_upcoming_events(self):
        event = Event.objects.create(
            team=self.team,
            title="This Week Service",
            created_by=self.admin,
            start_datetime=timezone.now() + timedelta(days=2),
            end_datetime=timezone.now() + timedelta(days=2, hours=2),
            category=EventCategory.WORSHIP,
            is_published=True,
        )
        client = self.get_client(self.member)
        response = client.get(f"/a/{self.team.slug}/")
        self.assertContains(response, "This Week Service")

    def test_dashboard_shows_stats(self):
        client = self.get_client(self.member)
        response = client.get(f"/a/{self.team.slug}/")
        # Should show team member count
        self.assertContains(response, "Team Members")

    def test_dashboard_shows_recent_blasts(self):
        MessageBlast.objects.create(
            team=self.team,
            subject="Welcome Everyone",
            body="Hello!",
            channel=NotificationChannel.EMAIL,
            status=BlastStatus.SENT,
            created_by=self.admin,
        )
        client = self.get_client(self.admin)
        response = client.get(f"/a/{self.team.slug}/")
        self.assertContains(response, "Welcome Everyone")

    def test_dashboard_requires_login(self):
        client = Client()
        response = client.get(f"/a/{self.team.slug}/")
        self.assertEqual(response.status_code, 302)
