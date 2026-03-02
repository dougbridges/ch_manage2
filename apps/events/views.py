"""
Event CRUD views.

Handles listing, creating, editing, deleting events, and the event detail page.
All views are team-scoped and use function-based views with permission decorators.
"""

from django.contrib import messages
from django.core.paginator import Paginator
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext_lazy as _

from apps.teams.decorators import login_and_team_required, team_admin_required, team_coordinator_required

from .forms import EventForm
from .models import Event, EventCategory


@login_and_team_required
def event_list(request, team_slug):
    """List upcoming events for the team with optional filtering."""
    events = (
        Event.objects.filter(team=request.team, is_published=True)
        .select_related("created_by")
        .prefetch_related("volunteer_slots")
        .order_by("start_datetime")
    )

    # Category filter
    category = request.GET.get("category", "")
    if category:
        events = events.filter(category=category)

    # Date range filter
    date_from = request.GET.get("date_from", "")
    date_to = request.GET.get("date_to", "")
    if date_from:
        events = events.filter(start_datetime__date__gte=date_from)
    if date_to:
        events = events.filter(start_datetime__date__lte=date_to)

    # Search by title
    q = request.GET.get("q", "")
    if q:
        events = events.filter(title__icontains=q)

    # Pagination
    paginator = Paginator(events, 20)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(request, "events/event_list.html", {
        "events": page_obj,
        "page_obj": page_obj,
        "categories": EventCategory.choices,
        "filter_category": category,
        "filter_date_from": date_from,
        "filter_date_to": date_to,
        "filter_q": q,
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
