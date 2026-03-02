"""
Rotation engine for generating volunteer shift assignments.

Supports round-robin and weighted strategies, with blackout-date filtering
and fairness tracking.
"""

import logging
from collections import defaultdict
from datetime import date

from django.db import models

from .models import Availability, RotationMembership, RotationSchedule, ScheduledShift, ShiftStatus

logger = logging.getLogger(__name__)


def generate_rotation(
    schedule: RotationSchedule,
    dates: list[date],
) -> list[ScheduledShift]:
    """
    Generate ScheduledShift records for a rotation schedule across the given dates.

    Args:
        schedule: The rotation schedule to generate shifts for.
        dates: List of dates to fill with shift assignments.

    Returns:
        List of newly created ScheduledShift instances.
    """
    if schedule.rotation_strategy == "round_robin":
        return _generate_round_robin(schedule, dates)
    elif schedule.rotation_strategy == "weighted":
        return _generate_weighted(schedule, dates)
    else:
        logger.info("Manual rotation strategy for %s — skipping auto-generation", schedule)
        return []


def _get_members_and_blackouts(
    schedule: RotationSchedule,
    dates: list[date],
) -> tuple[list[RotationMembership], dict[int, set[date]]]:
    """
    Fetch active rotation members and their blackout dates for the given date range.

    Returns:
        Tuple of (ordered memberships, dict mapping volunteer_id -> set of blackout dates).
    """
    memberships = list(
        schedule.memberships.filter(volunteer__is_active=True)
        .select_related("volunteer", "volunteer__user")
        .order_by("order")
    )

    if not memberships:
        return [], {}

    volunteer_ids = [m.volunteer_id for m in memberships]
    blackouts: dict[int, set[date]] = defaultdict(set)

    if dates:
        min_date, max_date = min(dates), max(dates)
        unavailable = Availability.objects.filter(
            volunteer_id__in=volunteer_ids,
            date__gte=min_date,
            date__lte=max_date,
            is_available=False,
        )
        for av in unavailable:
            blackouts[av.volunteer_id].add(av.date)

    return memberships, blackouts


def _get_existing_shift_dates(schedule: RotationSchedule, dates: list[date]) -> set[date]:
    """Return dates that already have shifts for this schedule."""
    if not dates:
        return set()
    return set(
        ScheduledShift.objects.filter(
            schedule=schedule,
            date__in=dates,
        ).values_list("date", flat=True)
    )


def _generate_round_robin(
    schedule: RotationSchedule,
    dates: list[date],
) -> list[ScheduledShift]:
    """
    Round-robin assignment: cycle through volunteers in order, skipping blackout dates.

    If a volunteer is unavailable, try the next one. If all are unavailable
    for a date, that date is left unfilled.
    """
    memberships, blackouts = _get_members_and_blackouts(schedule, dates)
    if not memberships:
        return []

    existing_dates = _get_existing_shift_dates(schedule, dates)
    new_dates = [d for d in dates if d not in existing_dates]
    if not new_dates:
        return []

    shifts = []
    pointer = 0
    num_members = len(memberships)

    for shift_date in sorted(new_dates):
        assigned = False
        for attempt in range(num_members):
            membership = memberships[(pointer + attempt) % num_members]
            volunteer = membership.volunteer
            if shift_date not in blackouts.get(volunteer.pk, set()):
                shift = ScheduledShift.objects.create(
                    schedule=schedule,
                    volunteer=volunteer,
                    event=schedule.event,
                    team=schedule.team,
                    date=shift_date,
                    status=ShiftStatus.SCHEDULED,
                )
                shifts.append(shift)
                pointer = (pointer + attempt + 1) % num_members
                assigned = True
                break

        if not assigned:
            logger.warning(
                "No available volunteer for %s on %s", schedule.name, shift_date
            )

    return shifts


def _generate_weighted(
    schedule: RotationSchedule,
    dates: list[date],
) -> list[ScheduledShift]:
    """
    Weighted assignment: volunteers with higher weight are scheduled more often.

    Uses a running count to distribute shifts proportionally to weight.
    The volunteer with the highest "deficit" (weight ratio minus actual assignments)
    gets the next shift.
    """
    memberships, blackouts = _get_members_and_blackouts(schedule, dates)
    if not memberships:
        return []

    existing_dates = _get_existing_shift_dates(schedule, dates)
    new_dates = [d for d in dates if d not in existing_dates]
    if not new_dates:
        return []

    # Track assignment counts for weighted fairness
    total_weight = sum(m.weight for m in memberships)
    assignment_counts: dict[int, int] = {m.volunteer_id: 0 for m in memberships}

    # Include existing shifts in count for fairness
    existing_counts = (
        ScheduledShift.objects.filter(
            schedule=schedule,
            volunteer_id__in=[m.volunteer_id for m in memberships],
        )
        .values("volunteer_id")
        .annotate(count=models.Count("id"))
    )
    for row in existing_counts:
        assignment_counts[row["volunteer_id"]] = row["count"]

    shifts = []
    for shift_date in sorted(new_dates):
        # Sort candidates by deficit: (expected_ratio - actual_ratio), descending
        total_assigned = sum(assignment_counts.values()) or 1
        candidates = []
        for m in memberships:
            if shift_date in blackouts.get(m.volunteer_id, set()):
                continue
            expected_ratio = m.weight / total_weight
            actual_ratio = assignment_counts[m.volunteer_id] / total_assigned
            deficit = expected_ratio - actual_ratio
            candidates.append((deficit, m))

        candidates.sort(key=lambda x: x[0], reverse=True)

        if candidates:
            _, membership = candidates[0]
            volunteer = membership.volunteer
            shift = ScheduledShift.objects.create(
                schedule=schedule,
                volunteer=volunteer,
                event=schedule.event,
                team=schedule.team,
                date=shift_date,
                status=ShiftStatus.SCHEDULED,
            )
            shifts.append(shift)
            assignment_counts[volunteer.pk] += 1
        else:
            logger.warning(
                "No available volunteer for %s on %s", schedule.name, shift_date
            )

    return shifts
