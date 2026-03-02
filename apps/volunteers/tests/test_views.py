"""
Tests for volunteer views: profiles, availability, rotations, shifts.
"""

from datetime import date
from unittest.mock import patch

from django.urls import reverse

from ..models import Availability, RotationSchedule, ScheduledShift, ShiftStatus, VolunteerProfile
from .base import (
    VolunteerTestBase,
    add_rotation_member,
    create_event,
    create_rotation,
    create_shift,
    create_volunteer_profile,
)


class VolunteerListViewTest(VolunteerTestBase):

    def test_coordinator_can_view(self):
        client = self.get_client(self.coordinator_user)
        url = reverse("volunteers:volunteer_list", args=[self.team.slug])
        response = client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_member_cannot_view(self):
        client = self.get_client(self.member_user)
        url = reverse("volunteers:volunteer_list", args=[self.team.slug])
        response = client.get(url)
        self.assertEqual(response.status_code, 404)


class MyVolunteerProfileViewTest(VolunteerTestBase):

    def test_member_can_access(self):
        client = self.get_client(self.member_user)
        url = reverse("volunteers:my_volunteer_profile", args=[self.team.slug])
        response = client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_creates_profile_on_first_visit(self):
        client = self.get_client(self.member_user)
        url = reverse("volunteers:my_volunteer_profile", args=[self.team.slug])
        client.get(url)
        self.assertTrue(VolunteerProfile.objects.filter(team=self.team, user=self.member_user).exists())

    def test_update_profile(self):
        client = self.get_client(self.member_user)
        url = reverse("volunteers:my_volunteer_profile", args=[self.team.slug])
        data = {"max_services_per_month": 2, "is_active": True, "notes": "Only mornings"}
        response = client.post(url, data)
        self.assertEqual(response.status_code, 302)
        profile = VolunteerProfile.objects.get(team=self.team, user=self.member_user)
        self.assertEqual(profile.max_services_per_month, 2)


class VolunteerProfileDetailViewTest(VolunteerTestBase):

    def test_coordinator_can_view(self):
        profile = create_volunteer_profile(self.team, self.member_user)
        client = self.get_client(self.coordinator_user)
        url = reverse("volunteers:volunteer_profile_detail", args=[self.team.slug, profile.pk])
        response = client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_member_cannot_access_others(self):
        profile = create_volunteer_profile(self.team, self.coordinator_user)
        client = self.get_client(self.member_user)
        url = reverse("volunteers:volunteer_profile_detail", args=[self.team.slug, profile.pk])
        response = client.get(url)
        self.assertEqual(response.status_code, 404)


class MyAvailabilityViewTest(VolunteerTestBase):

    def test_member_can_access(self):
        client = self.get_client(self.member_user)
        url = reverse("volunteers:my_availability", args=[self.team.slug])
        response = client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_toggle_blackout(self):
        client = self.get_client(self.member_user)
        url = reverse("volunteers:my_availability", args=[self.team.slug])
        # First POST creates blackout
        response = client.post(url, {"date": "2026-03-15"})
        self.assertEqual(response.status_code, 302)
        profile = VolunteerProfile.objects.get(team=self.team, user=self.member_user)
        self.assertTrue(Availability.objects.filter(volunteer=profile, date=date(2026, 3, 15)).exists())

        # Second POST removes it
        response = client.post(url, {"date": "2026-03-15"})
        self.assertFalse(Availability.objects.filter(volunteer=profile, date=date(2026, 3, 15)).exists())


class RotationListViewTest(VolunteerTestBase):

    def test_coordinator_can_view(self):
        client = self.get_client(self.coordinator_user)
        url = reverse("volunteers:rotation_list", args=[self.team.slug])
        response = client.get(url)
        self.assertEqual(response.status_code, 200)


class RotationCreateViewTest(VolunteerTestBase):

    def test_coordinator_can_create(self):
        event = create_event(self.team, self.admin_user)
        client = self.get_client(self.coordinator_user)
        url = reverse("volunteers:rotation_create", args=[self.team.slug])
        data = {
            "name": "Test Rotation",
            "event": event.pk,
            "slot_role_name": "Ushers",
            "rotation_strategy": "round_robin",
            "is_active": True,
        }
        response = client.post(url, data)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(RotationSchedule.objects.filter(name="Test Rotation").exists())


class RotationDetailViewTest(VolunteerTestBase):

    def test_shows_rotation(self):
        rotation = create_rotation(self.team)
        client = self.get_client(self.coordinator_user)
        url = reverse("volunteers:rotation_detail", args=[self.team.slug, rotation.pk])
        response = client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, rotation.name)


class RotationGenerateViewTest(VolunteerTestBase):

    def test_generate_creates_shifts(self):
        event = create_event(self.team, self.admin_user)
        rotation = create_rotation(self.team, event)
        profile = create_volunteer_profile(self.team, self.member_user)
        add_rotation_member(rotation, profile, order=0)

        client = self.get_client(self.coordinator_user)
        url = reverse("volunteers:rotation_generate", args=[self.team.slug, rotation.pk])
        data = {"start_date": "2026-03-01", "end_date": "2026-03-29"}
        response = client.post(url, data)
        self.assertEqual(response.status_code, 302)
        self.assertGreater(ScheduledShift.objects.filter(schedule=rotation).count(), 0)


class MyShiftsViewTest(VolunteerTestBase):

    def test_member_can_view(self):
        client = self.get_client(self.member_user)
        url = reverse("volunteers:my_shifts", args=[self.team.slug])
        response = client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_shows_upcoming_shifts(self):
        event = create_event(self.team, self.admin_user)
        rotation = create_rotation(self.team, event)
        profile = create_volunteer_profile(self.team, self.member_user)
        create_shift(rotation, profile, date(2026, 4, 1))

        client = self.get_client(self.member_user)
        url = reverse("volunteers:my_shifts", args=[self.team.slug])
        response = client.get(url)
        self.assertContains(response, rotation.name)


class ShiftConfirmDeclineViewTest(VolunteerTestBase):

    def test_confirm_shift(self):
        event = create_event(self.team, self.admin_user)
        rotation = create_rotation(self.team, event)
        profile = create_volunteer_profile(self.team, self.member_user)
        shift = create_shift(rotation, profile, date(2026, 4, 1))

        client = self.get_client(self.member_user)
        url = reverse("volunteers:shift_confirm", args=[self.team.slug, shift.pk])
        response = client.post(url)
        self.assertEqual(response.status_code, 302)
        shift.refresh_from_db()
        self.assertEqual(shift.status, ShiftStatus.CONFIRMED)

    def test_decline_shift(self):
        event = create_event(self.team, self.admin_user)
        rotation = create_rotation(self.team, event)
        profile = create_volunteer_profile(self.team, self.member_user)
        shift = create_shift(rotation, profile, date(2026, 4, 1))

        client = self.get_client(self.member_user)
        url = reverse("volunteers:shift_decline", args=[self.team.slug, shift.pk])
        response = client.post(url)
        self.assertEqual(response.status_code, 302)
        shift.refresh_from_db()
        self.assertEqual(shift.status, ShiftStatus.DECLINED)

    def test_confirm_after_decline(self):
        event = create_event(self.team, self.admin_user)
        rotation = create_rotation(self.team, event)
        profile = create_volunteer_profile(self.team, self.member_user)
        shift = create_shift(rotation, profile, date(2026, 4, 1), status=ShiftStatus.DECLINED)

        client = self.get_client(self.member_user)
        url = reverse("volunteers:shift_confirm", args=[self.team.slug, shift.pk])
        response = client.post(url)
        shift.refresh_from_db()
        self.assertEqual(shift.status, ShiftStatus.CONFIRMED)

    def test_other_user_cannot_confirm(self):
        event = create_event(self.team, self.admin_user)
        rotation = create_rotation(self.team, event)
        profile = create_volunteer_profile(self.team, self.member_user)
        shift = create_shift(rotation, profile, date(2026, 4, 1))

        client = self.get_client(self.coordinator_user)
        url = reverse("volunteers:shift_confirm", args=[self.team.slug, shift.pk])
        response = client.post(url)
        self.assertEqual(response.status_code, 404)
