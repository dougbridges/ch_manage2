"""
CSV export views for the events app.

Provides CSV downloads for event signups and event listings.
Only available to coordinators and admins.
"""



import csv

from django.http import HttpResponse
from django.utils.translation import gettext_lazy as _

from apps.teams.decorators import team_coordinator_required

from .models import Event, VolunteerSignup


@team_coordinator_required
def export_event_signups(request, team_slug, pk):
    """Export all signups for a specific event as CSV."""
    event = Event.objects.get(pk=pk, team=request.team)
    signups = (
        VolunteerSignup.objects.filter(slot__event=event)
        .select_related("volunteer", "slot")
        .order_by("slot__role_name", "volunteer__first_name")
    )

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="event-{event.pk}-signups.csv"'

    writer = csv.writer(response)
    writer.writerow([
        str(_("Role")),
        str(_("Volunteer Name")),
        str(_("Email")),
        str(_("Status")),
        str(_("Note")),
        str(_("Signed Up At")),
    ])

    for signup in signups:
        writer.writerow([
            signup.slot.role_name,
            signup.volunteer.get_full_name() or signup.volunteer.email,
            signup.volunteer.email,
            signup.get_status_display(),
            signup.note,
            signup.created_at.strftime("%Y-%m-%d %H:%M") if signup.created_at else "",
        ])

    return response


@team_coordinator_required
def export_events_list(request, team_slug):
    """Export all team events as CSV."""
    events = Event.objects.filter(team=request.team).order_by("start_datetime")

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="events.csv"'

    writer = csv.writer(response)
    writer.writerow([
        str(_("Title")),
        str(_("Category")),
        str(_("Start")),
        str(_("End")),
        str(_("Location")),
        str(_("Published")),
        str(_("Created By")),
    ])

    for event in events:
        writer.writerow([
            event.title,
            event.get_category_display(),
            event.start_datetime.strftime("%Y-%m-%d %H:%M"),
            event.end_datetime.strftime("%Y-%m-%d %H:%M"),
            event.location,
            str(_("Yes")) if event.is_published else str(_("No")),
            event.created_by.get_full_name() if event.created_by else "",
        ])

    return response
