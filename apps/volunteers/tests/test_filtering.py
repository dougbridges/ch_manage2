"""
Tests for volunteer list filtering and CSV exports (Phase 6B/6C).
"""

from .base import VolunteerTestBase, create_volunteer_profile


class VolunteerFilterTest(VolunteerTestBase):
    """Tests for the volunteer list filtering feature."""

    def test_filter_by_name(self):
        create_volunteer_profile(self.team, self.member_user)
        create_volunteer_profile(self.team, self.admin_user)

        client = self.get_client(self.coordinator_user)
        url = f"/a/{self.team.slug}/volunteers/?q=member"
        response = client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_filter_active_only(self):
        p1 = create_volunteer_profile(self.team, self.member_user, is_active=True)
        p2 = create_volunteer_profile(self.team, self.admin_user, is_active=False)

        client = self.get_client(self.coordinator_user)
        url = f"/a/{self.team.slug}/volunteers/?active=yes"
        response = client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_filter_inactive_only(self):
        create_volunteer_profile(self.team, self.member_user, is_active=True)
        create_volunteer_profile(self.team, self.admin_user, is_active=False)

        client = self.get_client(self.coordinator_user)
        url = f"/a/{self.team.slug}/volunteers/?active=no"
        response = client.get(url)
        self.assertEqual(response.status_code, 200)


class VolunteerExportTest(VolunteerTestBase):
    """Tests for volunteer CSV export functionality."""

    def test_export_roster_csv(self):
        create_volunteer_profile(self.team, self.member_user)
        client = self.get_client(self.coordinator_user)
        url = f"/a/{self.team.slug}/volunteers/export/roster/"
        response = client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv")
        content = response.content.decode()
        self.assertIn("member", content.lower())

    def test_export_shifts_csv(self):
        client = self.get_client(self.coordinator_user)
        url = f"/a/{self.team.slug}/volunteers/export/shifts/"
        response = client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv")

    def test_export_requires_coordinator(self):
        client = self.get_client(self.member_user)
        url = f"/a/{self.team.slug}/volunteers/export/roster/"
        response = client.get(url)
        self.assertIn(response.status_code, [302, 403, 404])
