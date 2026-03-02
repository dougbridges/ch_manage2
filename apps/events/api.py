"""
DRF API views for the events app.

Provides event CRUD, slot management, and volunteer signup endpoints.
"""

from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.teams.models import Membership
from apps.teams.roles import ROLE_ADMIN, ROLE_COORDINATOR

from .models import Event, SignupStatus, VolunteerSignup, VolunteerSlot
from .serializers import (
    EventDetailSerializer,
    EventListSerializer,
    EventWriteSerializer,
    VolunteerSlotSerializer,
    VolunteerSlotWriteSerializer,
)


class IsTeamMember(permissions.BasePermission):
    """Check the user is a member of the team from the URL."""

    def has_permission(self, request, view):
        team_slug = view.kwargs.get("team_slug")
        if not team_slug:
            return False
        return Membership.objects.filter(team__slug=team_slug, user=request.user).exists()


class IsCoordinatorOrAdmin(permissions.BasePermission):
    """Check the user has coordinator or admin role."""

    def has_permission(self, request, view):
        team_slug = view.kwargs.get("team_slug")
        if not team_slug:
            return False
        return Membership.objects.filter(
            team__slug=team_slug, user=request.user, role__in=[ROLE_ADMIN, ROLE_COORDINATOR]
        ).exists()


class IsAdmin(permissions.BasePermission):
    """Check the user has admin role."""

    def has_permission(self, request, view):
        team_slug = view.kwargs.get("team_slug")
        if not team_slug:
            return False
        return Membership.objects.filter(team__slug=team_slug, user=request.user, role=ROLE_ADMIN).exists()


class EventViewSet(viewsets.ModelViewSet):
    """
    API endpoint for events.

    GET: All team members. POST: Coordinator+. PUT/PATCH: Coordinator+. DELETE: Admin only.
    """

    def get_queryset(self):
        team_slug = self.kwargs.get("team_slug")
        return Event.objects.filter(team__slug=team_slug).select_related("created_by").order_by("-start_datetime")

    def get_serializer_class(self):
        if self.action == "list":
            return EventListSerializer
        if self.action in ["create", "update", "partial_update"]:
            return EventWriteSerializer
        return EventDetailSerializer

    def get_permissions(self):
        if self.action in ["create", "update", "partial_update"]:
            return [permissions.IsAuthenticated(), IsCoordinatorOrAdmin()]
        if self.action == "destroy":
            return [permissions.IsAuthenticated(), IsAdmin()]
        return [permissions.IsAuthenticated(), IsTeamMember()]

    def perform_create(self, serializer):
        from apps.teams.models import Team

        team = Team.objects.get(slug=self.kwargs["team_slug"])
        serializer.save(team=team, created_by=self.request.user)


class SlotViewSet(viewsets.ModelViewSet):
    """
    API endpoint for volunteer slots on an event.

    Nested under /events/<id>/slots/.
    GET: All team members. POST/PUT/DELETE: Coordinator+.
    """

    def get_queryset(self):
        return VolunteerSlot.objects.filter(
            event_id=self.kwargs.get("event_pk"),
            event__team__slug=self.kwargs.get("team_slug"),
        ).prefetch_related("signups__volunteer")

    def get_serializer_class(self):
        if self.action in ["create", "update", "partial_update"]:
            return VolunteerSlotWriteSerializer
        return VolunteerSlotSerializer

    def get_permissions(self):
        if self.action in ["create", "update", "partial_update", "destroy"]:
            return [permissions.IsAuthenticated(), IsCoordinatorOrAdmin()]
        return [permissions.IsAuthenticated(), IsTeamMember()]

    def perform_create(self, serializer):
        event = Event.objects.get(
            pk=self.kwargs["event_pk"],
            team__slug=self.kwargs["team_slug"],
        )
        serializer.save(event=event, team=event.team)

    @action(detail=True, methods=["post", "delete"], url_path="signup")
    def signup(self, request, team_slug=None, event_pk=None, pk=None):
        """Sign up (POST) or cancel (DELETE) the current user's slot signup."""
        slot = self.get_object()

        if request.method == "DELETE":
            try:
                existing = VolunteerSignup.objects.get(slot=slot, volunteer=request.user)
                existing.status = SignupStatus.CANCELLED
                existing.save()
                return Response({"detail": "Signup cancelled."})
            except VolunteerSignup.DoesNotExist:
                return Response({"detail": "Not signed up."}, status=status.HTTP_400_BAD_REQUEST)

        # POST — sign up
        if slot.is_full:
            return Response({"detail": "Slot is full."}, status=status.HTTP_400_BAD_REQUEST)

        signup_obj, created = VolunteerSignup.objects.get_or_create(
            slot=slot,
            volunteer=request.user,
            team=slot.team,
            defaults={"status": SignupStatus.CONFIRMED},
        )
        if not created and signup_obj.status == SignupStatus.CANCELLED:
            signup_obj.status = SignupStatus.CONFIRMED
            signup_obj.save()
        elif not created:
            return Response({"detail": "Already signed up."}, status=status.HTTP_400_BAD_REQUEST)

        return Response({"detail": "Signed up."}, status=status.HTTP_201_CREATED)
