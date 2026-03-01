"""
Event CRUD views.

Handles listing, creating, editing, deleting events, and the event detail page.
All views are team-scoped and use function-based views with permission decorators.
"""

from django.contrib import messages
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext_lazy as _

from apps.teams.decorators import login_and_team_required, team_admin_required, team_coordinator_required

from .forms import EventForm
from .models import Event


@login_and_team_required
def event_list(request, team_slug):
    """List upcoming events for the team."""
    events = Event.objects.filter(team=request.team, is_published=True).order_by("start_datetime")
    return render(request, "events/event_list.html", {
        "events": events,
        "active_tab": "events",
    })


@login_and_team_required
def event_detail(request, team_slug, pk):
    """Show event details with volunteer slots."""
    event = get_object_or_404(Event, pk=pk, team=request.team)
    if not event.is_published:
        # Only coordinators+ can see unpublished events
        from apps.teams.roles import is_coordinator
        if not is_coordinator(request.user, request.team):
            raise Http404
    slots = event.volunteer_slots.prefetch_related("signups__volunteer").all()
    return render(request, "events/event_detail.html", {
        "event": event,
        "slots": slots,
        "active_tab": "events",
    })


@team_coordinator_required
def event_create(request, team_slug):
    """Create a new event."""
    if request.method == "POST":
        form = EventForm(request.POST)
        if form.is_valid():
            event = form.save(commit=False)
            event.team = request.team
            event.created_by = request.user
            event.save()
            messages.success(request, _("Event created successfully."))
            return redirect("events:event_detail", team_slug=team_slug, pk=event.pk)
    else:
        form = EventForm()
    return render(request, "events/event_form.html", {
        "form": form,
        "active_tab": "events",
    })


@team_coordinator_required
def event_edit(request, team_slug, pk):
    """Edit an existing event."""
    event = get_object_or_404(Event, pk=pk, team=request.team)
    if request.method == "POST":
        form = EventForm(request.POST, instance=event)
        if form.is_valid():
            form.save()
            messages.success(request, _("Event updated successfully."))
            return redirect("events:event_detail", team_slug=team_slug, pk=event.pk)
    else:
        form = EventForm(instance=event)
    return render(request, "events/event_form.html", {
        "form": form,
        "event": event,
        "active_tab": "events",
    })


@team_admin_required
def event_delete(request, team_slug, pk):
    """Delete an event (admin only)."""
    event = get_object_or_404(Event, pk=pk, team=request.team)
    if request.method == "POST":
        event.delete()
        messages.success(request, _("Event deleted."))
        return redirect("events:event_list", team_slug=team_slug)
    return render(request, "events/event_confirm_delete.html", {
        "event": event,
        "active_tab": "events",
    })
