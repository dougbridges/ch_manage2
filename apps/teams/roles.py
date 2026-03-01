from __future__ import annotations

from django.contrib.auth.models import AnonymousUser

from apps.users.models import CustomUser

ROLE_ADMIN = "admin"
ROLE_COORDINATOR = "coordinator"
ROLE_MEMBER = "member"

ROLE_CHOICES = (
    (ROLE_ADMIN, "Administrator"),
    (ROLE_COORDINATOR, "Coordinator"),
    (ROLE_MEMBER, "Member"),
)


def is_member(user: CustomUser | AnonymousUser, team) -> bool:
    if not user.is_authenticated:
        return False
    if not team:
        return False
    return team.members.filter(id=user.id).exists()


def is_admin(user: CustomUser | AnonymousUser, team) -> bool:
    if not user.is_authenticated:
        return False
    if not team:
        return False

    from .models import Membership

    return Membership.objects.filter(team=team, user=user, role=ROLE_ADMIN).exists()


def is_coordinator(user: CustomUser | AnonymousUser, team) -> bool:
    """Check if user has coordinator role or higher (admin) on this team."""
    if not user.is_authenticated:
        return False
    if not team:
        return False

    from .models import Membership

    return Membership.objects.filter(
        team=team, user=user, role__in=[ROLE_ADMIN, ROLE_COORDINATOR]
    ).exists()
