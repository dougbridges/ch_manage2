"""
DRF API views for the notifications app.

Provides blast management endpoints (admin-only).
"""

from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.teams.models import Membership
from apps.teams.roles import ROLE_ADMIN

from .models import BlastStatus, MessageBlast, MessageRecipient, NotificationChannel, RecipientStatus
from .serializers import MessageBlastDetailSerializer, MessageBlastListSerializer, MessageBlastWriteSerializer


class IsAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        team_slug = view.kwargs.get("team_slug")
        return Membership.objects.filter(
            team__slug=team_slug, user=request.user, role=ROLE_ADMIN
        ).exists()


class BlastViewSet(viewsets.ModelViewSet):
    """
    API endpoint for message blasts (admin only).

    Supports create, list, retrieve, and send actions.
    """

    def get_queryset(self):
        team_slug = self.kwargs.get("team_slug")
        return MessageBlast.objects.filter(team__slug=team_slug).select_related("created_by")

    def get_serializer_class(self):
        if self.action == "list":
            return MessageBlastListSerializer
        if self.action in ["create", "update", "partial_update"]:
            return MessageBlastWriteSerializer
        return MessageBlastDetailSerializer

    def get_permissions(self):
        return [permissions.IsAuthenticated(), IsAdmin()]

    def perform_create(self, serializer):
        from apps.teams.models import Team
        team = Team.objects.get(slug=self.kwargs["team_slug"])
        blast = serializer.save(team=team, created_by=self.request.user, recipient_filter={"all": True})

        # Auto-create recipient records for all team members
        from apps.notifications.models import ContactPreference
        memberships = Membership.objects.filter(team=team).select_related("user")
        recipients = []
        for membership in memberships:
            user = membership.user
            pref = ContactPreference.objects.filter(team=team, user=user).first()
            if blast.channel == NotificationChannel.EMAIL:
                if pref and not pref.receive_email:
                    continue
            elif blast.channel == NotificationChannel.SMS:
                if not pref or not pref.receive_sms or not pref.phone_number:
                    continue
            recipients.append(MessageRecipient(
                blast=blast, user=user, team=team,
                channel=blast.channel, status=RecipientStatus.PENDING,
            ))
        MessageRecipient.objects.bulk_create(recipients)

    @action(detail=True, methods=["post"])
    def send(self, request, team_slug=None, pk=None):
        """Trigger sending a blast."""
        blast = self.get_object()
        if blast.status != BlastStatus.DRAFT:
            return Response({"detail": "Blast already sent or in progress."}, status=400)

        from .tasks import send_blast
        blast.status = BlastStatus.SENDING
        blast.save()
        send_blast.delay(blast.pk)
        return Response({"detail": "Blast is being sent."})
