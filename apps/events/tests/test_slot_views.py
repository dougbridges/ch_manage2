"""
Tests for volunteer slot CRUD and signup/cancel views.
"""

from django.test import Client
from django.urls import reverse

from ..models import SignupStatus, VolunteerSignup, VolunteerSlot
from .base import EventTestBase, create_event, create_signup, create_slot


class SlotCreateViewTest(EventTestBase):
    def test_member_cannot_create_slot(self):
        event = create_event(self.team, self.admin_user)
        client = self.get_client(self.member_user)
        url = reverse("events:slot_create", args=[self.team.slug, event.pk])
        response = client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_coordinator_can_create_slot(self):
        event = create_event(self.team, self.admin_user)
        client = self.get_client(self.coordinator_user)
        url = reverse("events:slot_create", args=[self.team.slug, event.pk])
        response = client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_create_slot_post(self):
        event = create_event(self.team, self.admin_user)
        client = self.get_client(self.coordinator_user)
        url = reverse("events:slot_create", args=[self.team.slug, event.pk])
        data = {"role_name": "Sound Technician", "slots_needed": 2}
        response = client.post(url, data)
        self.assertEqual(response.status_code, 302)
        slot = VolunteerSlot.objects.get(role_name="Sound Technician")
        self.assertEqual(slot.event, event)
        self.assertEqual(slot.team, self.team)


class SlotEditViewTest(EventTestBase):
    def test_coordinator_can_edit_slot(self):
        event = create_event(self.team, self.admin_user)
        slot = create_slot(event, "Greeter")
        client = self.get_client(self.coordinator_user)
        url = reverse("events:slot_edit", args=[self.team.slug, event.pk, slot.pk])
        response = client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_edit_slot_post(self):
        event = create_event(self.team, self.admin_user)
        slot = create_slot(event, "Greeter", 1)
        client = self.get_client(self.coordinator_user)
        url = reverse("events:slot_edit", args=[self.team.slug, event.pk, slot.pk])
        data = {"role_name": "Head Greeter", "slots_needed": 3}
        response = client.post(url, data)
        self.assertEqual(response.status_code, 302)
        slot.refresh_from_db()
        self.assertEqual(slot.role_name, "Head Greeter")
        self.assertEqual(slot.slots_needed, 3)


class SlotDeleteViewTest(EventTestBase):
    def test_coordinator_can_delete_slot(self):
        event = create_event(self.team, self.admin_user)
        slot = create_slot(event)
        slot_pk = slot.pk
        client = self.get_client(self.coordinator_user)
        url = reverse("events:slot_delete", args=[self.team.slug, event.pk, slot.pk])
        response = client.post(url)
        self.assertEqual(response.status_code, 302)
        self.assertFalse(VolunteerSlot.objects.filter(pk=slot_pk).exists())

    def test_member_cannot_delete_slot(self):
        event = create_event(self.team, self.admin_user)
        slot = create_slot(event)
        client = self.get_client(self.member_user)
        url = reverse("events:slot_delete", args=[self.team.slug, event.pk, slot.pk])
        response = client.post(url)
        self.assertEqual(response.status_code, 404)


class SlotSignupViewTest(EventTestBase):
    def test_member_can_signup(self):
        event = create_event(self.team, self.admin_user)
        slot = create_slot(event, "Nursery", 2)
        client = self.get_client(self.member_user)
        url = reverse("events:slot_signup", args=[self.team.slug, event.pk, slot.pk])
        response = client.post(url)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(VolunteerSignup.objects.filter(slot=slot, volunteer=self.member_user).exists())

    def test_signup_full_slot(self):
        """Signing up for a full slot should show a warning."""
        event = create_event(self.team, self.admin_user)
        slot = create_slot(event, "Solo Singer", 1)
        create_signup(slot, self.coordinator_user)  # fill the slot
        client = self.get_client(self.member_user)
        url = reverse("events:slot_signup", args=[self.team.slug, event.pk, slot.pk])
        response = client.post(url)
        self.assertEqual(response.status_code, 302)
        # Should not create a signup since slot is full
        self.assertFalse(VolunteerSignup.objects.filter(slot=slot, volunteer=self.member_user).exists())

    def test_duplicate_signup_prevented(self):
        event = create_event(self.team, self.admin_user)
        slot = create_slot(event, "Food Prep", 5)
        create_signup(slot, self.member_user)
        client = self.get_client(self.member_user)
        url = reverse("events:slot_signup", args=[self.team.slug, event.pk, slot.pk])
        response = client.post(url)
        self.assertEqual(response.status_code, 302)
        # Should still be only 1 signup
        self.assertEqual(VolunteerSignup.objects.filter(slot=slot, volunteer=self.member_user).count(), 1)

    def test_reactivate_cancelled_signup(self):
        event = create_event(self.team, self.admin_user)
        slot = create_slot(event, "Parking", 3)
        signup = create_signup(slot, self.member_user, SignupStatus.CANCELLED)
        client = self.get_client(self.member_user)
        url = reverse("events:slot_signup", args=[self.team.slug, event.pk, slot.pk])
        response = client.post(url)
        signup.refresh_from_db()
        self.assertEqual(signup.status, SignupStatus.CONFIRMED)

    def test_htmx_returns_partial(self):
        event = create_event(self.team, self.admin_user)
        slot = create_slot(event, "Nursery", 5)
        client = self.get_client(self.member_user)
        url = reverse("events:slot_signup", args=[self.team.slug, event.pk, slot.pk])
        response = client.post(url, HTTP_HX_REQUEST="true")
        self.assertEqual(response.status_code, 200)
        # Should return a partial template, not a redirect
        self.assertContains(response, "Nursery")

    def test_non_member_cannot_signup(self):
        event = create_event(self.team, self.admin_user)
        slot = create_slot(event)
        client = self.get_client(self.non_member_user)
        url = reverse("events:slot_signup", args=[self.team.slug, event.pk, slot.pk])
        response = client.post(url)
        self.assertEqual(response.status_code, 404)


class SlotCancelSignupViewTest(EventTestBase):
    def test_cancel_own_signup(self):
        event = create_event(self.team, self.admin_user)
        slot = create_slot(event)
        signup = create_signup(slot, self.member_user)
        client = self.get_client(self.member_user)
        url = reverse("events:slot_cancel_signup", args=[self.team.slug, event.pk, slot.pk])
        response = client.post(url)
        self.assertEqual(response.status_code, 302)
        signup.refresh_from_db()
        self.assertEqual(signup.status, SignupStatus.CANCELLED)

    def test_cancel_nonexistent_signup(self):
        """Cancelling when not signed up should not error."""
        event = create_event(self.team, self.admin_user)
        slot = create_slot(event)
        client = self.get_client(self.member_user)
        url = reverse("events:slot_cancel_signup", args=[self.team.slug, event.pk, slot.pk])
        response = client.post(url)
        self.assertEqual(response.status_code, 302)

    def test_htmx_cancel_returns_partial(self):
        event = create_event(self.team, self.admin_user)
        slot = create_slot(event, "Greeter", 3)
        create_signup(slot, self.member_user)
        client = self.get_client(self.member_user)
        url = reverse("events:slot_cancel_signup", args=[self.team.slug, event.pk, slot.pk])
        response = client.post(url, HTTP_HX_REQUEST="true")
        self.assertEqual(response.status_code, 200)
