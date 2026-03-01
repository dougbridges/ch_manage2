"""
Volunteer slot and signup views.

Handles CRUD for volunteer slots within events, plus signup/cancel actions.
Slot signup and cancel are HTMX-friendly, returning partial HTML when requested via HTMX.
"""

from django.contrib import messages
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext_lazy as _

from apps.teams.decorators import login_and_team_required, team_coordinator_required

from .forms import VolunteerSlotForm
from .models import Event, SignupStatus, VolunteerSignup, VolunteerSlot


@team_coordinator_required
def slot_create(request, team_slug, event_pk):
    """Add a volunteer slot to an event."""
    event = get_object_or_404(Event, pk=event_pk, team=request.team)
    if request.method == "POST":
        form = VolunteerSlotForm(request.POST)
        if form.is_valid():
            slot = form.save(commit=False)
            slot.event = event
            slot.team = request.team
            slot.save()
            messages.success(request, _("Volunteer slot added."))
            return redirect("events:event_detail", team_slug=team_slug, pk=event.pk)
    else:
        form = VolunteerSlotForm()
    return render(request, "events/components/slot_form.html", {
        "form": form,
        "event": event,
        "active_tab": "events",
    })


@team_coordinator_required
def slot_edit(request, team_slug, event_pk, slot_pk):
    """Edit a volunteer slot."""
    event = get_object_or_404(Event, pk=event_pk, team=request.team)
    slot = get_object_or_404(VolunteerSlot, pk=slot_pk, event=event)
    if request.method == "POST":
        form = VolunteerSlotForm(request.POST, instance=slot)
        if form.is_valid():
            form.save()
            messages.success(request, _("Volunteer slot updated."))
            return redirect("events:event_detail", team_slug=team_slug, pk=event.pk)
    else:
        form = VolunteerSlotForm(instance=slot)
    return render(request, "events/components/slot_form.html", {
        "form": form,
        "event": event,
        "slot": slot,
        "active_tab": "events",
    })


@team_coordinator_required
def slot_delete(request, team_slug, event_pk, slot_pk):
    """Delete a volunteer slot."""
    event = get_object_or_404(Event, pk=event_pk, team=request.team)
    slot = get_object_or_404(VolunteerSlot, pk=slot_pk, event=event)
    if request.method == "POST":
        slot.delete()
        messages.success(request, _("Volunteer slot removed."))
        return redirect("events:event_detail", team_slug=team_slug, pk=event.pk)
    raise Http404


@login_and_team_required
def slot_signup(request, team_slug, event_pk, slot_pk):
    """Sign up the current user for a volunteer slot."""
    event = get_object_or_404(Event, pk=event_pk, team=request.team)
    slot = get_object_or_404(VolunteerSlot, pk=slot_pk, event=event)

    if request.method == "POST":
        # Check if already signed up
        existing = VolunteerSignup.objects.filter(slot=slot, volunteer=request.user).first()
        if existing and existing.status != SignupStatus.CANCELLED:
            messages.warning(request, _("You are already signed up for this slot."))
        elif existing and existing.status == SignupStatus.CANCELLED:
            # Re-activate cancelled signup
            existing.status = SignupStatus.CONFIRMED
            existing.save()
            messages.success(request, _("You have been signed up again."))
        elif slot.is_full:
            messages.warning(request, _("This slot is full."))
        else:
            VolunteerSignup.objects.create(
                slot=slot,
                volunteer=request.user,
                team=request.team,
                status=SignupStatus.CONFIRMED,
            )
            messages.success(request, _("You have been signed up!"))

        # Return HTMX partial or redirect
        if request.htmx:
            slots = event.volunteer_slots.prefetch_related("signups__volunteer").all()
            return render(request, "events/components/slot_list.html", {
                "event": event,
                "slots": slots,
            })
        return redirect("events:event_detail", team_slug=team_slug, pk=event.pk)
    raise Http404


@login_and_team_required
def slot_cancel_signup(request, team_slug, event_pk, slot_pk):
    """Cancel the current user's signup for a volunteer slot."""
    event = get_object_or_404(Event, pk=event_pk, team=request.team)
    slot = get_object_or_404(VolunteerSlot, pk=slot_pk, event=event)

    if request.method == "POST":
        signup = VolunteerSignup.objects.filter(
            slot=slot, volunteer=request.user
        ).exclude(status=SignupStatus.CANCELLED).first()
        if signup:
            signup.status = SignupStatus.CANCELLED
            signup.save()
            messages.success(request, _("Your signup has been cancelled."))
        else:
            messages.warning(request, _("You are not signed up for this slot."))

        if request.htmx:
            slots = event.volunteer_slots.prefetch_related("signups__volunteer").all()
            return render(request, "events/components/slot_list.html", {
                "event": event,
                "slots": slots,
            })
        return redirect("events:event_detail", team_slug=team_slug, pk=event.pk)
    raise Http404
