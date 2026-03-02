"""
Tests for the volunteers REST API.
"""

from datetime import date

from rest_framework import status
from rest_framework.test import APIClient

from ..models import ShiftStatus
from .base import (
    VolunteerTestBase,
    add_rotation_member,
    create_event,
    create_rotation,
    create_shift,
    create_volunteer_profile,
)


class VolunteerProfileAPITest(VolunteerTestBase):

    def get_api_client(self, user):
        client = APIClient()
        client.login(username=user.email, password="testpass123")
        return client

    def test_list_own_profile(self):
        create_volunteer_profile(self.team, self.member_user)
        client = self.get_api_client(self.member_user)
        url = f"/api/a/{self.team.slug}/volunteers/profiles/"
        response = client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)

    def test_coordinator_sees_all(self):
        create_volunteer_profile(self.team, self.member_user)
        create_volunteer_profile(self.team, self.admin_user)
        client = self.get_api_client(self.coordinator_user)
        url = f"/api/a/{self.team.slug}/volunteers/profiles/"
        response = client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 2)

    def test_update_own_profile(self):
        profile = create_volunteer_profile(self.team, self.member_user)
        client = self.get_api_client(self.member_user)
        url = f"/api/a/{self.team.slug}/volunteers/profiles/{profile.pk}/"
        response = client.patch(url, {"max_services_per_month": 2}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        profile.refresh_from_db()
        self.assertEqual(profile.max_services_per_month, 2)

    def test_non_member_denied(self):
        client = self.get_api_client(self.non_member_user)
        url = f"/api/a/{self.team.slug}/volunteers/profiles/"
        response = client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class ShiftAPITest(VolunteerTestBase):

    def get_api_client(self, user):
        client = APIClient()
        client.login(username=user.email, password="testpass123")
        return client

    def test_list_own_shifts(self):
        event = create_event(self.team, self.admin_user)
        rotation = create_rotation(self.team, event)
        profile = create_volunteer_profile(self.team, self.member_user)
        create_shift(rotation, profile, date(2026, 4, 1))

        client = self.get_api_client(self.member_user)
        url = f"/api/a/{self.team.slug}/volunteers/shifts/"
        response = client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)

    def test_confirm_shift_via_api(self):
        event = create_event(self.team, self.admin_user)
        rotation = create_rotation(self.team, event)
        profile = create_volunteer_profile(self.team, self.member_user)
        shift = create_shift(rotation, profile, date(2026, 4, 1))

        client = self.get_api_client(self.member_user)
        url = f"/api/a/{self.team.slug}/volunteers/shifts/{shift.pk}/confirm/"
        response = client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        shift.refresh_from_db()
        self.assertEqual(shift.status, ShiftStatus.CONFIRMED)

    def test_decline_shift_via_api(self):
        event = create_event(self.team, self.admin_user)
        rotation = create_rotation(self.team, event)
        profile = create_volunteer_profile(self.team, self.member_user)
        shift = create_shift(rotation, profile, date(2026, 4, 1))

        client = self.get_api_client(self.member_user)
        url = f"/api/a/{self.team.slug}/volunteers/shifts/{shift.pk}/decline/"
        response = client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        shift.refresh_from_db()
        self.assertEqual(shift.status, ShiftStatus.DECLINED)

    def test_cannot_confirm_others_shift(self):
        event = create_event(self.team, self.admin_user)
        rotation = create_rotation(self.team, event)
        profile = create_volunteer_profile(self.team, self.member_user)
        shift = create_shift(rotation, profile, date(2026, 4, 1))

        client = self.get_api_client(self.coordinator_user)
        url = f"/api/a/{self.team.slug}/volunteers/shifts/{shift.pk}/confirm/"
        response = client.post(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
