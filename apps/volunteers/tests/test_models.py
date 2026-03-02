"""
Tests for volunteer models: VolunteerProfile, Availability, RotationSchedule,
RotationMembership, ScheduledShift.
"""

from datetime import date

from django.db import IntegrityError

from ..models import RotationStrategy, ShiftStatus
from .base import (
    VolunteerTestBase,
    add_rotation_member,
    create_blackout,
    create_event,
    create_rotation,
    create_shift,
    create_volunteer_profile,
)


class VolunteerProfileModelTest(VolunteerTestBase):

    def test_create_profile(self):
        profile = create_volunteer_profile(self.team, self.member_user)
        self.assertEqual(profile.team, self.team)
        self.assertEqual(profile.user, self.member_user)
        self.assertTrue(profile.is_active)

    def test_unique_together_team_user(self):
        create_volunteer_profile(self.team, self.member_user)
        with self.assertRaises(IntegrityError):
            create_volunteer_profile(self.team, self.member_user)

    def test_str(self):
        profile = create_volunteer_profile(self.team, self.member_user)
        self.assertIn(str(self.member_user), str(profile))

    def test_default_skills_empty_list(self):
        profile = create_volunteer_profile(self.team, self.member_user)
        self.assertEqual(profile.skills, [])

    def test_skills_json(self):
        profile = create_volunteer_profile(
            self.team, self.member_user, skills=["nursery", "ushers"]
        )
        self.assertEqual(profile.skills, ["nursery", "ushers"])


class AvailabilityModelTest(VolunteerTestBase):

    def test_create_blackout(self):
        profile = create_volunteer_profile(self.team, self.member_user)
        av = create_blackout(profile, date(2026, 3, 15))
        self.assertFalse(av.is_available)
        self.assertEqual(av.date, date(2026, 3, 15))

    def test_unique_together_volunteer_date(self):
        profile = create_volunteer_profile(self.team, self.member_user)
        create_blackout(profile, date(2026, 3, 15))
        with self.assertRaises(IntegrityError):
            create_blackout(profile, date(2026, 3, 15))

    def test_ordering_by_date(self):
        profile = create_volunteer_profile(self.team, self.member_user)
        create_blackout(profile, date(2026, 3, 20))
        create_blackout(profile, date(2026, 3, 10))
        from ..models import Availability
        avails = list(Availability.objects.filter(volunteer=profile))
        self.assertEqual(avails[0].date, date(2026, 3, 10))


class RotationScheduleModelTest(VolunteerTestBase):

    def test_create_rotation(self):
        event = create_event(self.team, self.admin_user)
        rotation = create_rotation(self.team, event)
        self.assertEqual(rotation.name, "Sunday Nursery Rotation")
        self.assertEqual(rotation.event, event)

    def test_rotation_without_event(self):
        rotation = create_rotation(self.team)
        self.assertIsNone(rotation.event)

    def test_ordering_by_name(self):
        create_rotation(self.team, name="Alpha")
        create_rotation(self.team, name="Beta")
        from ..models import RotationSchedule
        rotations = list(RotationSchedule.objects.filter(team=self.team))
        self.assertEqual(rotations[0].name, "Alpha")


class RotationMembershipModelTest(VolunteerTestBase):

    def test_add_member_to_rotation(self):
        profile = create_volunteer_profile(self.team, self.member_user)
        rotation = create_rotation(self.team)
        membership = add_rotation_member(rotation, profile, order=1, weight=2)
        self.assertEqual(membership.order, 1)
        self.assertEqual(membership.weight, 2)

    def test_unique_together_schedule_volunteer(self):
        profile = create_volunteer_profile(self.team, self.member_user)
        rotation = create_rotation(self.team)
        add_rotation_member(rotation, profile)
        with self.assertRaises(IntegrityError):
            add_rotation_member(rotation, profile)


class ScheduledShiftModelTest(VolunteerTestBase):

    def test_create_shift(self):
        event = create_event(self.team, self.admin_user)
        rotation = create_rotation(self.team, event)
        profile = create_volunteer_profile(self.team, self.member_user)
        shift = create_shift(rotation, profile, date(2026, 3, 15))
        self.assertEqual(shift.status, ShiftStatus.SCHEDULED)
        self.assertFalse(shift.reminder_sent)

    def test_unique_together_schedule_volunteer_date(self):
        event = create_event(self.team, self.admin_user)
        rotation = create_rotation(self.team, event)
        profile = create_volunteer_profile(self.team, self.member_user)
        create_shift(rotation, profile, date(2026, 3, 15))
        with self.assertRaises(IntegrityError):
            create_shift(rotation, profile, date(2026, 3, 15))

    def test_cascade_on_rotation_delete(self):
        event = create_event(self.team, self.admin_user)
        rotation = create_rotation(self.team, event)
        profile = create_volunteer_profile(self.team, self.member_user)
        create_shift(rotation, profile, date(2026, 3, 15))
        rotation.delete()
        from ..models import ScheduledShift
        self.assertEqual(ScheduledShift.objects.filter(volunteer=profile).count(), 0)
