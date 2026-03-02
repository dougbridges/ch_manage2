"""
Tests for notification list filtering and CSV exports (Phase 6B/6C).
"""

from .base import NotificationTestBase, create_blast, create_recipient


class BlastFilterTest(NotificationTestBase):
    """Tests for the blast list filtering feature."""

    def test_filter_by_status(self):
        create_blast(self.team, self.admin_user, subject="Sent Blast", status="sent")
        create_blast(self.team, self.admin_user, subject="Draft Blast", status="draft")

        client = self.get_client(self.coordinator_user)
        url = f"/a/{self.team.slug}/notifications/?status=sent"
        response = client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Sent Blast")
        self.assertNotContains(response, "Draft Blast")

    def test_filter_by_channel(self):
        create_blast(self.team, self.admin_user, subject="Email Blast", channel="email")
        create_blast(self.team, self.admin_user, subject="SMS Blast", channel="sms")

        client = self.get_client(self.coordinator_user)
        url = f"/a/{self.team.slug}/notifications/?channel=sms"
        response = client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "SMS Blast")
        self.assertNotContains(response, "Email Blast")

    def test_filter_by_search(self):
        create_blast(self.team, self.admin_user, subject="Welcome Blast")
        create_blast(self.team, self.admin_user, subject="Goodbye Blast")

        client = self.get_client(self.coordinator_user)
        url = f"/a/{self.team.slug}/notifications/?q=Welcome"
        response = client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Welcome Blast")
        self.assertNotContains(response, "Goodbye Blast")


class BlastExportTest(NotificationTestBase):
    """Tests for blast delivery report CSV export."""

    def test_export_blast_report_csv(self):
        blast = create_blast(self.team, self.admin_user, subject="Report Blast")
        create_recipient(blast, self.member_user)

        client = self.get_client(self.admin_user)
        url = f"/a/{self.team.slug}/notifications/{blast.pk}/export/"
        response = client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv")
        content = response.content.decode()
        self.assertIn("member", content.lower())

    def test_export_requires_admin(self):
        blast = create_blast(self.team, self.admin_user)
        client = self.get_client(self.coordinator_user)
        url = f"/a/{self.team.slug}/notifications/{blast.pk}/export/"
        response = client.get(url)
        self.assertIn(response.status_code, [302, 403])
