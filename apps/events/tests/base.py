"""
Test helpers for the events app.

Provides factory functions for creating test data (teams, users, events, slots, signups)
and a base test class that sets up common fixtures.
"""

from django.test import Client, TestCase, override_settings
from django.utils import timezone

from apps.teams.models import Membership, Team
from apps.teams.roles import ROLE_ADMIN, ROLE_COORDINATOR, ROLE_MEMBER
from apps.users.models import CustomUser

from ..models import Event, EventCategory, SignupStatus, VolunteerSignup, VolunteerSlot

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


def create_event(team: Team, created_by: CustomUser, **kwargs) -> Event:
    """Create a test event with sensible defaults."""
    defaults = {
        "title": "Sunday Worship",
        "description": "Weekly worship service",
        "location": "Main Sanctuary",
        "start_datetime": timezone.now() + timezone.timedelta(days=1),
        "end_datetime": timezone.now() + timezone.timedelta(days=1, hours=2),
        "category": EventCategory.WORSHIP,
        "is_published": True,
    }
    defaults.update(kwargs)
    return Event.objects.create(team=team, created_by=created_by, **defaults)


def create_slot(event: Event, role_name: str = "Ushers", slots_needed: int = 2) -> VolunteerSlot:
    """Create a volunteer slot for an event."""
    return VolunteerSlot.objects.create(
        event=event,
        team=event.team,
        role_name=role_name,
        slots_needed=slots_needed,
    )


def create_signup(slot: VolunteerSlot, user: CustomUser, status: str = SignupStatus.CONFIRMED) -> VolunteerSignup:
    """Create a volunteer signup."""
    return VolunteerSignup.objects.create(
        slot=slot,
        volunteer=user,
        team=slot.team,
        status=status,
    )


@override_settings(STORAGES=TEST_STORAGES)
class EventTestBase(TestCase):
    """
    Base test class for events app tests.

    Sets up a team with three users: admin, coordinator, and member.
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
