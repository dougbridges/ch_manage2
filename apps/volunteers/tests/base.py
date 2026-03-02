"""
Test helpers for the volunteers app.

Provides factory functions and a base test class for volunteer tests.
"""

from datetime import date, timedelta

from django.test import Client, TestCase, override_settings
from django.utils import timezone

from apps.events.models import Event, EventCategory
from apps.teams.models import Membership, Team
from apps.teams.roles import ROLE_ADMIN, ROLE_COORDINATOR, ROLE_MEMBER
from apps.users.models import CustomUser

from ..models import (
    Availability,
    RotationMembership,
    RotationSchedule,
    RotationStrategy,
    ScheduledShift,
    ShiftStatus,
    VolunteerProfile,
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
    return CustomUser.objects.create_user(username=email, email=email, password=password)


def create_team(name: str = "Test Church", slug: str = "test-church") -> Team:
    return Team.objects.create(name=name, slug=slug)


def add_member(team: Team, user: CustomUser, role: str = ROLE_MEMBER) -> Membership:
    return Membership.objects.create(team=team, user=user, role=role)


def create_volunteer_profile(team: Team, user: CustomUser, **kwargs) -> VolunteerProfile:
    defaults = {"is_active": True, "max_services_per_month": 4}
    defaults.update(kwargs)
    return VolunteerProfile.objects.create(team=team, user=user, **defaults)


def create_event(team: Team, created_by: CustomUser, **kwargs) -> Event:
    defaults = {
        "title": "Sunday Worship",
        "start_datetime": timezone.now() + timedelta(days=1),
        "end_datetime": timezone.now() + timedelta(days=1, hours=2),
        "category": EventCategory.WORSHIP,
        "is_published": True,
    }
    defaults.update(kwargs)
    return Event.objects.create(team=team, created_by=created_by, **defaults)


def create_rotation(team: Team, event: Event = None, **kwargs) -> RotationSchedule:
    defaults = {
        "name": "Sunday Nursery Rotation",
        "slot_role_name": "Nursery",
        "rotation_strategy": RotationStrategy.ROUND_ROBIN,
        "is_active": True,
    }
    defaults.update(kwargs)
    return RotationSchedule.objects.create(team=team, event=event, **defaults)


def add_rotation_member(
    rotation: RotationSchedule, profile: VolunteerProfile, order: int = 0, weight: int = 1
) -> RotationMembership:
    return RotationMembership.objects.create(
        schedule=rotation,
        volunteer=profile,
        team=rotation.team,
        order=order,
        weight=weight,
    )


def create_shift(schedule: RotationSchedule, profile: VolunteerProfile, shift_date: date, **kwargs) -> ScheduledShift:
    defaults = {
        "event": schedule.event,
        "status": ShiftStatus.SCHEDULED,
    }
    defaults.update(kwargs)
    return ScheduledShift.objects.create(
        schedule=schedule,
        volunteer=profile,
        team=schedule.team,
        date=shift_date,
        **defaults,
    )


def create_blackout(profile: VolunteerProfile, blackout_date: date) -> Availability:
    return Availability.objects.create(
        volunteer=profile,
        team=profile.team,
        date=blackout_date,
        is_available=False,
    )


@override_settings(STORAGES=TEST_STORAGES)
class VolunteerTestBase(TestCase):
    """Base test class with common volunteer fixtures."""

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
        client = Client()
        client.login(username=user.email, password="testpass123")
        return client
