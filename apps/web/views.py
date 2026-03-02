from datetime import timedelta

from django.conf import settings
from django.contrib import messages
from django.db.models import Count, Q
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from health_check.views import MainView

from apps.teams.decorators import login_and_team_required
from apps.teams.helpers import get_open_invitations_for_user


def home(request):
    if request.user.is_authenticated:
        team = request.default_team
        if team:
            return HttpResponseRedirect(reverse("web_team:home", args=[team.slug]))
        else:
            if (open_invitations := get_open_invitations_for_user(request.user)) and len(open_invitations) > 1:
                invitation = open_invitations[0]
                return HttpResponseRedirect(reverse("teams:accept_invitation", args=[invitation["id"]]))

            messages.info(
                request,
                _("Teams are enabled but you have no teams. Create a team below to access the rest of the dashboard."),
            )
            return HttpResponseRedirect(reverse("teams:manage_teams"))
    else:
        return render(request, "web/landing_page.html")


@login_and_team_required
def team_home(request, team_slug):
    """Church dashboard with upcoming events, shifts, recent blasts, and stats."""
    assert request.team.slug == team_slug
    now = timezone.now()
    week_ahead = now + timedelta(days=7)

    # Upcoming events (next 7 days)
    from apps.events.models import Event

    upcoming_events = (
        Event.objects.filter(
            team=request.team,
            is_published=True,
            start_datetime__gte=now,
            start_datetime__lte=week_ahead,
        )
        .prefetch_related("volunteer_slots")
        .order_by("start_datetime")[:5]
    )

    # My upcoming volunteer shifts (next 14 days)
    my_shifts = []
    try:
        from apps.volunteers.models import ScheduledShift, ShiftStatus, VolunteerProfile

        profile = VolunteerProfile.objects.filter(team=request.team, user=request.user).first()
        if profile:
            my_shifts = (
                ScheduledShift.objects.filter(
                    volunteer=profile,
                    date__gte=now.date(),
                    date__lte=(now + timedelta(days=14)).date(),
                )
                .exclude(status=ShiftStatus.DECLINED)
                .select_related("schedule", "event")
                .order_by("date")[:5]
            )
    except ImportError:
        pass

    # Recent blasts (last 5)
    recent_blasts = []
    try:
        from apps.notifications.models import MessageBlast

        recent_blasts = MessageBlast.objects.filter(team=request.team).order_by("-created_at")[:5]
    except ImportError:
        pass

    # Quick stats
    total_events = Event.objects.filter(
        team=request.team,
        is_published=True,
        start_datetime__gte=now,
    ).count()

    total_volunteers = 0
    try:
        total_volunteers = VolunteerProfile.objects.filter(team=request.team, is_active=True).count()
    except NameError:
        pass

    from apps.teams.models import Membership

    total_members = Membership.objects.filter(team=request.team).count()

    return render(
        request,
        "web/app_home.html",
        context={
            "team": request.team,
            "active_tab": "dashboard",
            "page_title": _("{team} Dashboard").format(team=request.team),
            "upcoming_events": upcoming_events,
            "my_shifts": my_shifts,
            "recent_blasts": recent_blasts,
            "total_events": total_events,
            "total_volunteers": total_volunteers,
            "total_members": total_members,
        },
    )


def simulate_error(request):
    raise Exception("This is a simulated error.")


class HealthCheck(MainView):
    def get(self, request, *args, **kwargs):
        tokens = settings.HEALTH_CHECK_TOKENS
        if tokens and request.GET.get("token") not in tokens:
            raise Http404
        return super().get(request, *args, **kwargs)
