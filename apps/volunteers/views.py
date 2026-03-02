"""
Volunteer views: profile management, availability, rotation schedules, and shifts.

Coordinators manage volunteers and rotations. Members manage their own profiles and shifts.
"""

from datetime import date, timedelta

from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_POST

from apps.teams.decorators import login_and_team_required, team_coordinator_required

from .forms import GenerateShiftsForm, RotationScheduleForm, VolunteerProfileForm
from .models import (
    Availability,
    RotationSchedule,
    ScheduledShift,
    ShiftStatus,
    VolunteerProfile,
)

# --- Volunteer List & Profiles ---


@team_coordinator_required
def volunteer_list(request, team_slug):
    """List all volunteer profiles for the team with optional filtering."""
    profiles = VolunteerProfile.objects.filter(team=request.team).select_related("user").order_by("user__first_name")

    # Search by name
    q = request.GET.get("q", "")
    if q:
        profiles = profiles.filter(
            Q(user__first_name__icontains=q) | Q(user__last_name__icontains=q) | Q(user__email__icontains=q)
        )

    # Active filter
    active = request.GET.get("active", "")
    if active == "yes":
        profiles = profiles.filter(is_active=True)
    elif active == "no":
        profiles = profiles.filter(is_active=False)

    # Pagination
    paginator = Paginator(profiles, 24)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(
        request,
        "volunteers/volunteer_list.html",
        {
            "profiles": page_obj,
            "page_obj": page_obj,
            "filter_q": q,
            "filter_active": active,
            "active_tab": "volunteers",
        },
    )


@login_and_team_required
def my_volunteer_profile(request, team_slug):
    """View/edit the current user's volunteer profile."""
    profile, created = VolunteerProfile.objects.get_or_create(
        team=request.team,
        user=request.user,
        defaults={"is_active": True},
    )
    if request.method == "POST":
        form = VolunteerProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, _("Volunteer profile updated."))
            return redirect("volunteers:my_volunteer_profile", team_slug=team_slug)
    else:
        form = VolunteerProfileForm(instance=profile)
    return render(
        request,
        "volunteers/volunteer_profile.html",
        {
            "form": form,
            "profile": profile,
            "is_own_profile": True,
            "active_tab": "volunteers",
        },
    )


@team_coordinator_required
def volunteer_profile_detail(request, team_slug, pk):
    """View/edit a specific volunteer's profile (coordinator view)."""
    profile = get_object_or_404(VolunteerProfile, pk=pk, team=request.team)
    if request.method == "POST":
        form = VolunteerProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, _("Volunteer profile updated."))
            return redirect("volunteers:volunteer_profile_detail", team_slug=team_slug, pk=pk)
    else:
        form = VolunteerProfileForm(instance=profile)
    return render(
        request,
        "volunteers/volunteer_profile.html",
        {
            "form": form,
            "profile": profile,
            "is_own_profile": False,
            "active_tab": "volunteers",
        },
    )


# --- Availability ---


@login_and_team_required
def my_availability(request, team_slug):
    """Manage own blackout dates with a calendar-style picker."""
    profile, _ = VolunteerProfile.objects.get_or_create(
        team=request.team,
        user=request.user,
        defaults={"is_active": True},
    )

    # Handle HTMX toggle of availability
    if request.method == "POST":
        date_str = request.POST.get("date")
        if date_str:
            target_date = date.fromisoformat(date_str)
            av, created = Availability.objects.get_or_create(
                volunteer=profile,
                team=request.team,
                date=target_date,
                defaults={"is_available": False},
            )
            if not created:
                # Toggle: if it was unavailable, delete the record (making them available)
                av.delete()
            if getattr(request, "htmx", False):
                return _render_availability_calendar(request, profile)
            return redirect("volunteers:my_availability", team_slug=team_slug)

    return _render_availability_calendar(request, profile, full_page=True)


def _render_availability_calendar(request, profile, full_page=False):
    """Render the availability calendar view."""
    today = timezone.now().date()
    year = int(request.GET.get("year", today.year))
    month = int(request.GET.get("month", today.month))

    # Build calendar data for the month
    import calendar

    cal = calendar.Calendar(firstweekday=6)  # Sunday first
    month_days = cal.monthdayscalendar(year, month)

    # Get blackout dates for this month
    blackout_dates = set(
        Availability.objects.filter(
            volunteer=profile,
            date__year=year,
            date__month=month,
            is_available=False,
        ).values_list("date", flat=True)
    )

    # Previous/next month navigation
    if month == 1:
        prev_year, prev_month = year - 1, 12
    else:
        prev_year, prev_month = year, month - 1
    if month == 12:
        next_year, next_month = year + 1, 1
    else:
        next_year, next_month = year, month + 1

    context = {
        "profile": profile,
        "month_days": month_days,
        "year": year,
        "month": month,
        "month_name": calendar.month_name[month],
        "blackout_dates": blackout_dates,
        "today": today,
        "prev_year": prev_year,
        "prev_month": prev_month,
        "next_year": next_year,
        "next_month": next_month,
        "active_tab": "volunteers",
    }

    if full_page:
        return render(request, "volunteers/availability.html", context)
    return render(request, "volunteers/components/availability_calendar.html", context)


# --- Rotation Schedules ---


@team_coordinator_required
def rotation_list(request, team_slug):
    """List all rotation schedules for the team."""
    rotations = RotationSchedule.objects.filter(team=request.team).select_related("event")
    return render(
        request,
        "volunteers/rotation_list.html",
        {
            "rotations": rotations,
            "active_tab": "volunteers",
        },
    )


@team_coordinator_required
def rotation_create(request, team_slug):
    """Create a new rotation schedule."""
    if request.method == "POST":
        form = RotationScheduleForm(request.POST, team=request.team)
        if form.is_valid():
            rotation = form.save(commit=False)
            rotation.team = request.team
            rotation.save()
            messages.success(request, _("Rotation schedule created."))
            return redirect("volunteers:rotation_detail", team_slug=team_slug, pk=rotation.pk)
    else:
        form = RotationScheduleForm(team=request.team)
    return render(
        request,
        "volunteers/rotation_form.html",
        {
            "form": form,
            "active_tab": "volunteers",
        },
    )


@team_coordinator_required
def rotation_detail(request, team_slug, pk):
    """View a rotation schedule with its members and upcoming shifts."""
    rotation = get_object_or_404(RotationSchedule, pk=pk, team=request.team)
    memberships = rotation.memberships.select_related("volunteer__user").order_by("order")
    upcoming_shifts = (
        rotation.shifts.filter(
            date__gte=timezone.now().date(),
        )
        .select_related("volunteer__user")
        .order_by("date")[:20]
    )
    return render(
        request,
        "volunteers/rotation_detail.html",
        {
            "rotation": rotation,
            "memberships": memberships,
            "upcoming_shifts": upcoming_shifts,
            "active_tab": "volunteers",
        },
    )


@team_coordinator_required
def rotation_edit(request, team_slug, pk):
    """Edit a rotation schedule."""
    rotation = get_object_or_404(RotationSchedule, pk=pk, team=request.team)
    if request.method == "POST":
        form = RotationScheduleForm(request.POST, instance=rotation, team=request.team)
        if form.is_valid():
            form.save()
            messages.success(request, _("Rotation schedule updated."))
            return redirect("volunteers:rotation_detail", team_slug=team_slug, pk=pk)
    else:
        form = RotationScheduleForm(instance=rotation, team=request.team)
    return render(
        request,
        "volunteers/rotation_form.html",
        {
            "form": form,
            "rotation": rotation,
            "active_tab": "volunteers",
        },
    )


@team_coordinator_required
def rotation_generate(request, team_slug, pk):
    """Generate shifts for a rotation schedule (POST only)."""
    rotation = get_object_or_404(RotationSchedule, pk=pk, team=request.team)
    if request.method == "POST":
        form = GenerateShiftsForm(request.POST)
        if form.is_valid():
            start = form.cleaned_data["start_date"]
            end = form.cleaned_data["end_date"]

            from .tasks import _get_schedule_dates

            dates = _get_schedule_dates(rotation, start, end)
            if not dates:
                # Fall back: generate weekly dates
                dates = []
                current = start
                while current <= end:
                    dates.append(current)
                    current += timedelta(days=7)

            from .rotation import generate_rotation

            shifts = generate_rotation(rotation, dates)
            messages.success(
                request,
                _("Generated %(count)d shifts.") % {"count": len(shifts)},
            )
        else:
            messages.error(request, _("Invalid date range."))
    return redirect("volunteers:rotation_detail", team_slug=team_slug, pk=rotation.pk)


@team_coordinator_required
def rotation_shifts(request, team_slug, pk):
    """View and manage all shifts for a rotation."""
    rotation = get_object_or_404(RotationSchedule, pk=pk, team=request.team)
    shifts = rotation.shifts.select_related("volunteer__user").order_by("date")
    return render(
        request,
        "volunteers/rotation_shifts.html",
        {
            "rotation": rotation,
            "shifts": shifts,
            "active_tab": "volunteers",
        },
    )


# --- My Shifts ---


@login_and_team_required
def my_shifts(request, team_slug):
    """View own upcoming shifts."""
    profile = VolunteerProfile.objects.filter(team=request.team, user=request.user).first()
    if profile:
        shifts = (
            ScheduledShift.objects.filter(
                volunteer=profile,
                date__gte=timezone.now().date(),
            )
            .select_related("schedule", "event")
            .order_by("date")
        )
    else:
        shifts = ScheduledShift.objects.none()
    return render(
        request,
        "volunteers/my_shifts.html",
        {
            "shifts": shifts,
            "profile": profile,
            "active_tab": "volunteers",
        },
    )


@login_and_team_required
@require_POST
def shift_confirm(request, team_slug, pk):
    """Confirm a scheduled shift (HTMX or redirect)."""
    profile = get_object_or_404(VolunteerProfile, team=request.team, user=request.user)
    shift = get_object_or_404(ScheduledShift, pk=pk, volunteer=profile)
    if shift.status in [ShiftStatus.SCHEDULED, ShiftStatus.DECLINED]:
        shift.status = ShiftStatus.CONFIRMED
        shift.save()
        messages.success(request, _("Shift confirmed."))
    if getattr(request, "htmx", False):
        return render(request, "volunteers/components/shift_card.html", {"shift": shift})
    return redirect("volunteers:my_shifts", team_slug=team_slug)


@login_and_team_required
@require_POST
def shift_decline(request, team_slug, pk):
    """Decline a scheduled shift (HTMX or redirect)."""
    profile = get_object_or_404(VolunteerProfile, team=request.team, user=request.user)
    shift = get_object_or_404(ScheduledShift, pk=pk, volunteer=profile)
    if shift.status in [ShiftStatus.SCHEDULED, ShiftStatus.CONFIRMED]:
        shift.status = ShiftStatus.DECLINED
        shift.save()
        messages.success(request, _("Shift declined."))
    if getattr(request, "htmx", False):
        return render(request, "volunteers/components/shift_card.html", {"shift": shift})
    return redirect("volunteers:my_shifts", team_slug=team_slug)
