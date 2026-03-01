"""
Tests for event models: creation, validation, querysets, and managers.
"""

from django.test import TestCase
from django.utils import timezone

from apps.teams.models import Team
from apps.users.models import CustomUser

from ..models import Event, EventCategory, SignupStatus, VolunteerSignup, VolunteerSlot
from .base import EventTestBase, create_event, create_signup, create_slot


class EventModelTest(EventTestBase):
    def test_create_event(self):
        event = create_event(self.team, self.admin_user)
        self.assertEqual(event.title, "Sunday Worship")
        self.assertEqual(event.team, self.team)
        self.assertEqual(event.created_by, self.admin_user)

    def test_event_str(self):
        event = create_event(self.team, self.admin_user, title="Potluck Dinner")
        self.assertEqual(str(event), "Potluck Dinner")

    def test_event_ordering(self):
        """Events should be ordered by start_datetime."""
        e1 = create_event(
            self.team, self.admin_user, title="Later",
            start_datetime=timezone.now() + timezone.timedelta(days=5),
            end_datetime=timezone.now() + timezone.timedelta(days=5, hours=2),
        )
        e2 = create_event(
            self.team, self.admin_user, title="Sooner",
            start_datetime=timezone.now() + timezone.timedelta(days=1),
            end_datetime=timezone.now() + timezone.timedelta(days=1, hours=2),
        )
        events = list(Event.objects.filter(team=self.team).order_by("start_datetime"))
        self.assertEqual(events[0], e2)
        self.assertEqual(events[1], e1)

    def test_event_category_choices(self):
        for value, label in EventCategory.choices:
            event = create_event(self.team, self.admin_user, category=value)
            self.assertEqual(event.category, value)
            event.delete()

    def test_event_get_absolute_url(self):
        event = create_event(self.team, self.admin_user)
        url = event.get_absolute_url()
        self.assertIn(self.team.slug, url)
        self.assertIn(str(event.pk), url)


class VolunteerSlotModelTest(EventTestBase):
    def test_create_slot(self):
        event = create_event(self.team, self.admin_user)
        slot = create_slot(event, "Nursery", 3)
        self.assertEqual(slot.role_name, "Nursery")
        self.assertEqual(slot.slots_needed, 3)
        self.assertEqual(slot.event, event)

    def test_slot_str(self):
        event = create_event(self.team, self.admin_user, title="VBS")
        slot = create_slot(event, "Games Leader")
        self.assertEqual(str(slot), "Games Leader — VBS")

    def test_slots_remaining(self):
        event = create_event(self.team, self.admin_user)
        slot = create_slot(event, "Ushers", slots_needed=2)
        self.assertEqual(slot.slots_remaining, 2)
        create_signup(slot, self.member_user)
        self.assertEqual(slot.slots_remaining, 1)

    def test_is_full(self):
        event = create_event(self.team, self.admin_user)
        slot = create_slot(event, "Sound Tech", slots_needed=1)
        self.assertFalse(slot.is_full)
        create_signup(slot, self.member_user)
        self.assertTrue(slot.is_full)

    def test_active_signups_excludes_cancelled(self):
        event = create_event(self.team, self.admin_user)
        slot = create_slot(event, "Greeter", slots_needed=2)
        create_signup(slot, self.member_user, SignupStatus.CONFIRMED)
        create_signup(slot, self.coordinator_user, SignupStatus.CANCELLED)
        self.assertEqual(slot.active_signups.count(), 1)

    def test_slot_cascade_delete_with_event(self):
        """Deleting an event should cascade-delete its slots."""
        event = create_event(self.team, self.admin_user)
        slot = create_slot(event)
        event_pk, slot_pk = event.pk, slot.pk
        event.delete()
        self.assertFalse(VolunteerSlot.objects.filter(pk=slot_pk).exists())


class VolunteerSignupModelTest(EventTestBase):
    def test_create_signup(self):
        event = create_event(self.team, self.admin_user)
        slot = create_slot(event)
        signup = create_signup(slot, self.member_user)
        self.assertEqual(signup.volunteer, self.member_user)
        self.assertEqual(signup.status, SignupStatus.CONFIRMED)

    def test_signup_str(self):
        event = create_event(self.team, self.admin_user)
        slot = create_slot(event, "Food Prep")
        signup = create_signup(slot, self.member_user)
        self.assertIn("Food Prep", str(signup))

    def test_unique_together_slot_volunteer(self):
        """A user can only sign up once per slot."""
        from django.db import IntegrityError

        event = create_event(self.team, self.admin_user)
        slot = create_slot(event)
        create_signup(slot, self.member_user)
        with self.assertRaises(IntegrityError):
            create_signup(slot, self.member_user)

    def test_signup_cascade_delete_with_slot(self):
        """Deleting a slot should cascade-delete its signups."""
        event = create_event(self.team, self.admin_user)
        slot = create_slot(event)
        signup = create_signup(slot, self.member_user)
        signup_pk = signup.pk
        slot.delete()
        self.assertFalse(VolunteerSignup.objects.filter(pk=signup_pk).exists())


class EventQuerySetTest(EventTestBase):
    def test_upcoming(self):
        past = create_event(
            self.team, self.admin_user, title="Past Event",
            start_datetime=timezone.now() - timezone.timedelta(days=2),
            end_datetime=timezone.now() - timezone.timedelta(days=2, hours=-2),
        )
        future = create_event(
            self.team, self.admin_user, title="Future Event",
            start_datetime=timezone.now() + timezone.timedelta(days=2),
            end_datetime=timezone.now() + timezone.timedelta(days=2, hours=2),
        )
        upcoming = Event.event_objects.filter(team=self.team).upcoming()
        self.assertIn(future, upcoming)
        self.assertNotIn(past, upcoming)

    def test_published(self):
        pub = create_event(self.team, self.admin_user, title="Published", is_published=True)
        draft = create_event(self.team, self.admin_user, title="Draft", is_published=False)
        published = Event.event_objects.filter(team=self.team).published()
        self.assertIn(pub, published)
        self.assertNotIn(draft, published)
