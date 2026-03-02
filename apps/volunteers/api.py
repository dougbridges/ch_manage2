"""
DRF API views for the volunteers app.

Provides volunteer profile and shift management endpoints.
"""

from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.teams.models import Membership
from apps.teams.roles import ROLE_ADMIN, ROLE_COORDINATOR

from .models import ScheduledShift, ShiftStatus, VolunteerProfile
from .serializers import ScheduledShiftSerializer, VolunteerProfileSerializer


class IsTeamMember(permissions.BasePermission):
    def has_permission(self, request, view):
        team_slug = view.kwargs.get("team_slug")
        return Membership.objects.filter(team__slug=team_slug, user=request.user).exists()


class IsCoordinatorOrAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        team_slug = view.kwargs.get("team_slug")
        return Membership.objects.filter(
            team__slug=team_slug, user=request.user, role__in=[ROLE_ADMIN, ROLE_COORDINATOR]
        ).exists()


class VolunteerProfileViewSet(viewsets.ModelViewSet):
    """
    API endpoint for volunteer profiles.

    Members can view/edit their own profile. Coordinators can view/edit all.
    """

    serializer_class = VolunteerProfileSerializer
    http_method_names = ["get", "put", "patch", "head", "options"]

    def get_queryset(self):
        team_slug = self.kwargs.get("team_slug")
        qs = VolunteerProfile.objects.filter(team__slug=team_slug).select_related("user")
        # Members can only see their own profile
        membership = Membership.objects.filter(
            team__slug=team_slug, user=self.request.user
        ).first()
        if membership and membership.role not in [ROLE_ADMIN, ROLE_COORDINATOR]:
            qs = qs.filter(user=self.request.user)
        return qs

    def get_permissions(self):
        return [permissions.IsAuthenticated(), IsTeamMember()]


class ShiftViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for scheduled shifts.

    Members see their own shifts. Coordinators see all.
    """

    serializer_class = ScheduledShiftSerializer

    def get_queryset(self):
        team_slug = self.kwargs.get("team_slug")
        qs = ScheduledShift.objects.filter(
            team__slug=team_slug,
        ).select_related("schedule", "volunteer__user", "event")

        membership = Membership.objects.filter(
            team__slug=team_slug, user=self.request.user
        ).first()
        if membership and membership.role not in [ROLE_ADMIN, ROLE_COORDINATOR]:
            qs = qs.filter(volunteer__user=self.request.user)
        return qs.order_by("date")

    def get_permissions(self):
        return [permissions.IsAuthenticated(), IsTeamMember()]

    @action(detail=True, methods=["post"])
    def confirm(self, request, team_slug=None, pk=None):
        """Confirm a scheduled shift."""
        shift = self.get_object()
        if shift.volunteer.user != request.user:
            return Response({"detail": "Not your shift."}, status=status.HTTP_403_FORBIDDEN)
        if shift.status in [ShiftStatus.SCHEDULED, ShiftStatus.DECLINED]:
            shift.status = ShiftStatus.CONFIRMED
            shift.save()
        return Response(ScheduledShiftSerializer(shift).data)

    @action(detail=True, methods=["post"])
    def decline(self, request, team_slug=None, pk=None):
        """Decline a scheduled shift."""
        shift = self.get_object()
        if shift.volunteer.user != request.user:
            return Response({"detail": "Not your shift."}, status=status.HTTP_403_FORBIDDEN)
        if shift.status in [ShiftStatus.SCHEDULED, ShiftStatus.CONFIRMED]:
            shift.status = ShiftStatus.DECLINED
            shift.save()
        return Response(ScheduledShiftSerializer(shift).data)
