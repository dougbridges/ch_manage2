"""
CSV export views for the volunteers app.

Provides CSV downloads for the volunteer roster and shift schedules.
Only available to coordinators and admins.
"""

import csv

from django.http import HttpResponse
from django.utils.translation import gettext_lazy as _

from apps.teams.decorators import team_coordinator_required

from .models import ScheduledShift, VolunteerProfile


@team_coordinator_required
def export_volunteer_roster(request, team_slug):
    """Export all volunteer profiles for the team as CSV."""
    profiles = (
        VolunteerProfile.objects.filter(team=request.team)
        .select_related("user")
        .order_by("user__first_name", "user__last_name")
    )

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="volunteer-roster.csv"'

    writer = csv.writer(response)
    writer.writerow([
        str(_("Name")),
        str(_("Email")),
        str(_("Active")),
        str(_("Max Services/Month")),
        str(_("Skills")),
        str(_("Notes")),
        str(_("Joined")),
    ])

    for profile in profiles:
        skills = ", ".join(profile.skills) if profile.skills else ""
        writer.writerow([
            profile.user.get_full_name() or profile.user.email,
            profile.user.email,
            str(_("Yes")) if profile.is_active else str(_("No")),
            profile.max_services_per_month,
            skills,
            profile.notes,
            profile.created_at.strftime("%Y-%m-%d") if profile.created_at else "",
        ])

    return response


@team_coordinator_required
def export_shift_schedule(request, team_slug):
    """Export all scheduled shifts for the team as CSV."""
    shifts = (
        ScheduledShift.objects.filter(team=request.team)
        .select_related("volunteer__user", "schedule", "event")
        .order_by("date", "schedule__name")
    )

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="shift-schedule.csv"'

    writer = csv.writer(response)
    writer.writerow([
        str(_("Date")),
        str(_("Schedule")),
        str(_("Volunteer")),
        str(_("Email")),
        str(_("Event")),
        str(_("Status")),
        str(_("Reminder Sent")),
    ])

    for shift in shifts:
        writer.writerow([
            shift.date.strftime("%Y-%m-%d"),
            shift.schedule.name,
            shift.volunteer.user.get_full_name() or shift.volunteer.user.email,
            shift.volunteer.user.email,
            shift.event.title if shift.event else "",
            shift.get_status_display(),
            str(_("Yes")) if shift.reminder_sent else str(_("No")),
        ])

    return response
