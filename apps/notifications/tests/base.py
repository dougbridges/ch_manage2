"""
Test helpers for the notifications app.

Provides factory functions and a base test class for notification tests.
"""

from django.test import Client, TestCase, override_settings

from apps.teams.models import Membership, Team
from apps.teams.roles import ROLE_ADMIN, ROLE_COORDINATOR, ROLE_MEMBER
from apps.users.models import CustomUser

from ..models import (
    BlastStatus,
    ContactPreference,
    MessageBlast,
    MessageRecipient,
    NotificationChannel,
    RecipientStatus,
)

TEST_STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}


def create_user(email: str, password: str = "testpass123") -> CustomUser:
    """Create a test user."""
    return CustomUser.objects.create_user(username=email, email=email, password=password)


def create_team(name: str = "Test Church", slug: str = "test-church") -> Team:
    """Create a test team."""
    return Team.objects.create(name=name, slug=slug)


def add_member(team: Team, user: CustomUser, role: str = ROLE_MEMBER) -> Membership:
    """Add a user to a team with the given role."""
    return Membership.objects.create(team=team, user=user, role=role)


def create_blast(team: Team, created_by: CustomUser, **kwargs) -> MessageBlast:
    """Create a test message blast with sensible defaults."""
    defaults = {
        "subject": "Test Blast",
        "body": "This is a test notification.",
        "channel": NotificationChannel.EMAIL,
        "status": BlastStatus.DRAFT,
    }
    defaults.update(kwargs)
    return MessageBlast.objects.create(team=team, created_by=created_by, **defaults)


def create_recipient(blast: MessageBlast, user: CustomUser, **kwargs) -> MessageRecipient:
    """Create a recipient record for a blast."""
    defaults = {
        "channel": blast.channel,
        "status": RecipientStatus.PENDING,
    }
    defaults.update(kwargs)
    return MessageRecipient.objects.create(blast=blast, user=user, team=blast.team, **defaults)


def create_preference(team: Team, user: CustomUser, **kwargs) -> ContactPreference:
    """Create a contact preference record."""
    defaults = {
        "receive_email": True,
        "receive_sms": False,
    }
    defaults.update(kwargs)
    return ContactPreference.objects.create(team=team, user=user, **defaults)


@override_settings(STORAGES=TEST_STORAGES)
class NotificationTestBase(TestCase):
    """
    Base test class for notifications app tests.

    Sets up a team with admin, coordinator, and member users.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.team = create_team()
        cls.admin_user = create_user("admin@church.com")
        cls.coordinator_user = create_user("coordinator@church.com")
        cls.member_user = create_user("member@church.com")
        cls.non_member_user = create_user("outsider@example.com")

        add_member(cls.team, cls.admin_user, ROLE_ADMIN)
        add_member(cls.team, cls.coordinator_user, ROLE_COORDINATOR)
        add_member(cls.team, cls.member_user, ROLE_MEMBER)

    def get_client(self, user: CustomUser) -> Client:
        """Return an authenticated client for the given user."""
        client = Client()
        client.login(username=user.email, password="testpass123")
        return client
