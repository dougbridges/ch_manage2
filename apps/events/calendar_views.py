"""
Calendar views for the events app.

Server-rendered monthly calendar grid with HTMX navigation for
previous/next month without full page reloads.
"""

import calendar
from datetime import date

from django.shortcuts import render
from django.utils import timezone

from apps.teams.decorators import login_and_team_required

from .models import Event


def _get_calendar_context(team, year: int, month: int) -> dict:
    """Build template context for the calendar grid."""
    cal = calendar.Calendar(firstweekday=6)  # Sunday-first for church context
    month_days = cal.monthdayscalendar(year, month)

    # Get events for this month
    events = Event.objects.filter(
        team=team,
        is_published=True,
        start_datetime__year=year,
        start_datetime__month=month,
    ).order_by("start_datetime")

    # Build a dict of day -> list of events for template rendering
    events_by_day: dict[int, list] = {}
    for event in events:
        day = event.start_datetime.day
        events_by_day.setdefault(day, []).append(event)

    # Calculate previous/next month
    if month == 1:
        prev_year, prev_month = year - 1, 12
    else:
        prev_year, prev_month = year, month - 1
    if month == 12:
        next_year, next_month = year + 1, 1
    else:
        next_year, next_month = year, month + 1

    today = date.today()

    return {
        "year": year,
        "month": month,
        "month_name": calendar.month_name[month],
        "month_days": month_days,
        "events_by_day": events_by_day,
        "prev_year": prev_year,
        "prev_month": prev_month,
        "next_year": next_year,
        "next_month": next_month,
        "today": today,
        "weekday_headers": ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"],
    }


@login_and_team_required
def event_calendar(request, team_slug):
    """Full calendar page for the current month."""
    now = timezone.now()
    context = _get_calendar_context(request.team, now.year, now.month)
    context["active_tab"] = "calendar"
    return render(request, "events/calendar.html", context)


@login_and_team_required
def event_calendar_month(request, team_slug, year, month):
    """
    Render a specific month's calendar.

    When requested via HTMX, returns just the grid partial for swapping.
    Otherwise returns the full calendar page.
    """
    year, month = int(year), int(month)
    # Clamp month to valid range
    if month < 1 or month > 12:
        now = timezone.now()
        year, month = now.year, now.month

    context = _get_calendar_context(request.team, year, month)
    context["active_tab"] = "calendar"

    if request.htmx:
        return render(request, "events/components/calendar_grid.html", context)
    return render(request, "events/calendar.html", context)
