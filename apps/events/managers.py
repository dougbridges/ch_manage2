"""
Custom querysets for the events app.

Provides date-range filtering methods on Event querysets:
.upcoming(), .past(), .in_month(year, month).
"""

from django.db import models
from django.utils import timezone


class EventQuerySet(models.QuerySet):
    """Custom queryset for Event with convenience date filters."""

    def upcoming(self):
        """Return events starting now or in the future."""
        return self.filter(start_datetime__gte=timezone.now()).order_by("start_datetime")

    def past(self):
        """Return events that have already ended."""
        return self.filter(end_datetime__lt=timezone.now()).order_by("-start_datetime")

    def in_month(self, year: int, month: int):
        """Return events occurring in the given year/month."""
        from calendar import monthrange

        _, last_day = monthrange(year, month)
        start = timezone.datetime(year, month, 1, tzinfo=timezone.get_current_timezone())
        end = timezone.datetime(year, month, last_day, 23, 59, 59, tzinfo=timezone.get_current_timezone())
        return self.filter(
            start_datetime__lte=end,
            end_datetime__gte=start,
        ).order_by("start_datetime")

    def published(self):
        """Return only published events."""
        return self.filter(is_published=True)
