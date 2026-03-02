"""
Notification views: blast list, compose, detail, send, and contact preferences.

Blast composition and sending are admin-only. Coordinators can view blast history.
All team members can manage their own contact preferences.
"""

from django.contrib import messages
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.teams.decorators import login_and_team_required, team_admin_required, team_coordinator_required
from apps.teams.models import Membership

from .forms import BlastComposeForm, ContactPreferenceForm
from .models import BlastStatus, ContactPreference, MessageBlast, MessageRecipient, NotificationChannel, RecipientStatus


@team_coordinator_required
def blast_list(request, team_slug):
    """List sent and scheduled message blasts with optional filtering."""
    blasts = MessageBlast.objects.filter(team=request.team).order_by("-created_at")

    # Status filter
    status = request.GET.get("status", "")
    if status:
        blasts = blasts.filter(status=status)

    # Channel filter
    channel = request.GET.get("channel", "")
    if channel:
        blasts = blasts.filter(channel=channel)

    # Search by subject
    q = request.GET.get("q", "")
    if q:
        blasts = blasts.filter(subject__icontains=q)

    # Pagination
    paginator = Paginator(blasts, 20)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(request, "notifications/blast_list.html", {
        "blasts": page_obj,
        "page_obj": page_obj,
        "statuses": BlastStatus.choices,
        "channels": NotificationChannel.choices,
        "filter_status": status,
        "filter_channel": channel,
        "filter_q": q,
        "active_tab": "notifications",
    })


@team_admin_required
def blast_compose(request, team_slug):
    """Compose a new message blast."""
    if request.method == "POST":
        form = BlastComposeForm(request.POST)
        if form.is_valid():
            blast = form.save(commit=False)
            blast.team = request.team
            blast.created_by = request.user
            blast.recipient_filter = {"all": True}
            blast.save()

            # Create recipient records for all team members
            memberships = Membership.objects.filter(team=request.team).select_related("user")
            recipients = []
            for membership in memberships:
                user = membership.user
                # Check contact preferences
                pref = ContactPreference.objects.filter(team=request.team, user=user).first()
                if blast.channel == NotificationChannel.EMAIL:
                    if pref and not pref.receive_email:
                        continue
                elif blast.channel == NotificationChannel.SMS:
                    if not pref or not pref.receive_sms or not pref.phone_number:
                        continue
                recipients.append(MessageRecipient(
                    blast=blast,
                    user=user,
                    team=request.team,
                    channel=blast.channel,
                    status=RecipientStatus.PENDING,
                ))
            MessageRecipient.objects.bulk_create(recipients)

            messages.success(request, _("Blast created with %(count)d recipients.") % {"count": len(recipients)})
            return redirect("notifications:blast_detail", team_slug=team_slug, pk=blast.pk)
    else:
        form = BlastComposeForm()
    return render(request, "notifications/blast_compose.html", {
        "form": form,
        "active_tab": "notifications",
    })


@team_coordinator_required
def blast_detail(request, team_slug, pk):
    """View blast details and delivery status."""
    blast = get_object_or_404(MessageBlast, pk=pk, team=request.team)
    recipients = blast.recipients.select_related("user").order_by("status")
    return render(request, "notifications/blast_detail.html", {
        "blast": blast,
        "recipients": recipients,
        "active_tab": "notifications",
    })


@team_admin_required
def blast_send(request, team_slug, pk):
    """Trigger sending a blast (POST only)."""
    blast = get_object_or_404(MessageBlast, pk=pk, team=request.team)
    if request.method == "POST":
        if blast.status != BlastStatus.DRAFT:
            messages.warning(request, _("This blast has already been sent or is in progress."))
        else:
            # Import here to avoid circular imports
            from .tasks import send_blast
            blast.status = BlastStatus.SENDING
            blast.save()
            send_blast.delay(blast.pk)
            messages.success(request, _("Blast is being sent."))
        return redirect("notifications:blast_detail", team_slug=team_slug, pk=blast.pk)
    return redirect("notifications:blast_detail", team_slug=team_slug, pk=blast.pk)


@login_and_team_required
def contact_preferences(request, team_slug):
    """Edit the current user's notification preferences."""
    pref, created = ContactPreference.objects.get_or_create(
        team=request.team,
        user=request.user,
        defaults={"receive_email": True, "receive_sms": False},
    )
    if request.method == "POST":
        form = ContactPreferenceForm(request.POST, instance=pref)
        if form.is_valid():
            form.save()
            messages.success(request, _("Notification preferences saved."))
            return redirect("notifications:contact_preferences", team_slug=team_slug)
    else:
        form = ContactPreferenceForm(instance=pref)
    return render(request, "notifications/contact_preferences.html", {
        "form": form,
        "active_tab": "notifications",
    })
