"""
Tests for the rotation algorithm: round_robin, weighted, availability filtering.
"""

from datetime import date

from ..models import RotationStrategy, ScheduledShift
from ..rotation import generate_rotation
from .base import (
    VolunteerTestBase,
    add_rotation_member,
    create_blackout,
    create_event,
    create_rotation,
    create_volunteer_profile,
)


class RoundRobinRotationTest(VolunteerTestBase):
    def test_round_robin_basic(self):
        event = create_event(self.team, self.admin_user)
        rotation = create_rotation(self.team, event, rotation_strategy=RotationStrategy.ROUND_ROBIN)
        p1 = create_volunteer_profile(self.team, self.admin_user)
        p2 = create_volunteer_profile(self.team, self.coordinator_user)
        p3 = create_volunteer_profile(self.team, self.member_user)
        add_rotation_member(rotation, p1, order=0)
        add_rotation_member(rotation, p2, order=1)
        add_rotation_member(rotation, p3, order=2)

        dates = [date(2026, 3, 1), date(2026, 3, 8), date(2026, 3, 15)]
        shifts = generate_rotation(rotation, dates)

        self.assertEqual(len(shifts), 3)
        self.assertEqual(shifts[0].volunteer, p1)
        self.assertEqual(shifts[1].volunteer, p2)
        self.assertEqual(shifts[2].volunteer, p3)

    def test_round_robin_wraps_around(self):
        event = create_event(self.team, self.admin_user)
        rotation = create_rotation(self.team, event)
        p1 = create_volunteer_profile(self.team, self.admin_user)
        p2 = create_volunteer_profile(self.team, self.coordinator_user)
        add_rotation_member(rotation, p1, order=0)
        add_rotation_member(rotation, p2, order=1)

        dates = [date(2026, 3, 1), date(2026, 3, 8), date(2026, 3, 15), date(2026, 3, 22)]
        shifts = generate_rotation(rotation, dates)

        self.assertEqual(len(shifts), 4)
        self.assertEqual(shifts[0].volunteer, p1)
        self.assertEqual(shifts[1].volunteer, p2)
        self.assertEqual(shifts[2].volunteer, p1)
        self.assertEqual(shifts[3].volunteer, p2)

    def test_round_robin_skips_blackout(self):
        event = create_event(self.team, self.admin_user)
        rotation = create_rotation(self.team, event)
        p1 = create_volunteer_profile(self.team, self.admin_user)
        p2 = create_volunteer_profile(self.team, self.coordinator_user)
        add_rotation_member(rotation, p1, order=0)
        add_rotation_member(rotation, p2, order=1)
        # p1 is unavailable on March 1
        create_blackout(p1, date(2026, 3, 1))

        dates = [date(2026, 3, 1), date(2026, 3, 8)]
        shifts = generate_rotation(rotation, dates)

        self.assertEqual(len(shifts), 2)
        self.assertEqual(shifts[0].volunteer, p2)  # p1 skipped

    def test_all_unavailable_skips_date(self):
        event = create_event(self.team, self.admin_user)
        rotation = create_rotation(self.team, event)
        p1 = create_volunteer_profile(self.team, self.admin_user)
        add_rotation_member(rotation, p1, order=0)
        create_blackout(p1, date(2026, 3, 1))

        dates = [date(2026, 3, 1)]
        shifts = generate_rotation(rotation, dates)

        self.assertEqual(len(shifts), 0)

    def test_single_volunteer(self):
        event = create_event(self.team, self.admin_user)
        rotation = create_rotation(self.team, event)
        p1 = create_volunteer_profile(self.team, self.admin_user)
        add_rotation_member(rotation, p1, order=0)

        dates = [date(2026, 3, 1), date(2026, 3, 8)]
        shifts = generate_rotation(rotation, dates)

        self.assertEqual(len(shifts), 2)
        self.assertTrue(all(s.volunteer == p1 for s in shifts))

    def test_no_members_returns_empty(self):
        event = create_event(self.team, self.admin_user)
        rotation = create_rotation(self.team, event)

        dates = [date(2026, 3, 1)]
        shifts = generate_rotation(rotation, dates)

        self.assertEqual(len(shifts), 0)

    def test_skips_existing_dates(self):
        event = create_event(self.team, self.admin_user)
        rotation = create_rotation(self.team, event)
        p1 = create_volunteer_profile(self.team, self.admin_user)
        add_rotation_member(rotation, p1, order=0)

        # Generate once
        dates = [date(2026, 3, 1)]
        generate_rotation(rotation, dates)

        # Generate again — should not duplicate
        shifts = generate_rotation(rotation, dates)
        self.assertEqual(len(shifts), 0)
        self.assertEqual(ScheduledShift.objects.filter(schedule=rotation).count(), 1)

    def test_inactive_volunteer_skipped(self):
        event = create_event(self.team, self.admin_user)
        rotation = create_rotation(self.team, event)
        p1 = create_volunteer_profile(self.team, self.admin_user, is_active=False)
        p2 = create_volunteer_profile(self.team, self.coordinator_user)
        add_rotation_member(rotation, p1, order=0)
        add_rotation_member(rotation, p2, order=1)

        dates = [date(2026, 3, 1)]
        shifts = generate_rotation(rotation, dates)

        self.assertEqual(len(shifts), 1)
        self.assertEqual(shifts[0].volunteer, p2)


class WeightedRotationTest(VolunteerTestBase):
    def test_weighted_basic(self):
        event = create_event(self.team, self.admin_user)
        rotation = create_rotation(self.team, event, rotation_strategy=RotationStrategy.WEIGHTED)
        p1 = create_volunteer_profile(self.team, self.admin_user)
        p2 = create_volunteer_profile(self.team, self.coordinator_user)
        add_rotation_member(rotation, p1, weight=3)
        add_rotation_member(rotation, p2, weight=1)

        dates = [date(2026, 3, d) for d in range(1, 9)]
        shifts = generate_rotation(rotation, dates)

        self.assertEqual(len(shifts), 8)
        p1_count = sum(1 for s in shifts if s.volunteer == p1)
        p2_count = sum(1 for s in shifts if s.volunteer == p2)
        # p1 should have roughly 3x more shifts than p2
        self.assertGreater(p1_count, p2_count)

    def test_weighted_with_blackout(self):
        event = create_event(self.team, self.admin_user)
        rotation = create_rotation(self.team, event, rotation_strategy=RotationStrategy.WEIGHTED)
        p1 = create_volunteer_profile(self.team, self.admin_user)
        p2 = create_volunteer_profile(self.team, self.coordinator_user)
        add_rotation_member(rotation, p1, weight=2)
        add_rotation_member(rotation, p2, weight=1)
        create_blackout(p1, date(2026, 3, 1))

        dates = [date(2026, 3, 1)]
        shifts = generate_rotation(rotation, dates)

        self.assertEqual(len(shifts), 1)
        self.assertEqual(shifts[0].volunteer, p2)

    def test_equal_weights(self):
        event = create_event(self.team, self.admin_user)
        rotation = create_rotation(self.team, event, rotation_strategy=RotationStrategy.WEIGHTED)
        p1 = create_volunteer_profile(self.team, self.admin_user)
        p2 = create_volunteer_profile(self.team, self.coordinator_user)
        add_rotation_member(rotation, p1, weight=1)
        add_rotation_member(rotation, p2, weight=1)

        dates = [date(2026, 3, d) for d in range(1, 5)]
        shifts = generate_rotation(rotation, dates)

        self.assertEqual(len(shifts), 4)
        p1_count = sum(1 for s in shifts if s.volunteer == p1)
        p2_count = sum(1 for s in shifts if s.volunteer == p2)
        self.assertEqual(p1_count, 2)
        self.assertEqual(p2_count, 2)


class ManualRotationTest(VolunteerTestBase):
    def test_manual_returns_empty(self):
        rotation = create_rotation(self.team, rotation_strategy=RotationStrategy.MANUAL)
        shifts = generate_rotation(rotation, [date(2026, 3, 1)])
        self.assertEqual(len(shifts), 0)
