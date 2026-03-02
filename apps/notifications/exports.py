"""
CSV export views for the notifications app.

Provides CSV downloads for blast delivery reports.
Only available to admins.
"""

import csv

from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext_lazy as _

from apps.teams.decorators import team_admin_required

from .models import MessageBlast


@team_admin_required
def export_blast_report(request, team_slug, pk):
    """Export delivery report for a specific blast as CSV."""
    blast = get_object_or_404(MessageBlast, pk=pk, team=request.team)
    recipients = blast.recipients.select_related("user").order_by("status", "user__first_name")

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="blast-{blast.pk}-report.csv"'

    writer = csv.writer(response)
    writer.writerow(
        [
            str(_("Recipient")),
            str(_("Email")),
            str(_("Channel")),
            str(_("Status")),
            str(_("Sent At")),
            str(_("Error")),
        ]
    )

    for recipient in recipients:
        writer.writerow(
            [
                recipient.user.get_full_name() or recipient.user.email,
                recipient.user.email,
                recipient.get_channel_display(),
                recipient.get_status_display(),
                recipient.sent_at.strftime("%Y-%m-%d %H:%M") if recipient.sent_at else "",
                recipient.error_message,
            ]
        )

    return response
