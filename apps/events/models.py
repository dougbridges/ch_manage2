"""
Event models for Planning Center Lite.

This module defines the core event management models: Event (the main calendar entry),
VolunteerSlot (positions that need filling), and VolunteerSignup (who signed up for what).
All models extend BaseTeamModel for automatic team scoping.
"""

from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from recurrence.fields import RecurrenceField

from apps.teams.models import BaseTeamModel

from .managers import EventQuerySet


class EventCategory(models.TextChoices):
    """Categories for church events."""

    WORSHIP = "worship", _("Worship")
    FELLOWSHIP = "fellowship", _("Fellowship")
    OUTREACH = "outreach", _("Outreach")
    YOUTH = "youth", _("Youth")
    OTHER = "other", _("Other")


class Event(BaseTeamModel):
    """
    A church event (service, potluck, VBS, youth trip, etc.).

    Events can be one-time or recurring (via django-recurrence RRULE field).
    Each event can have multiple VolunteerSlots attached to it.

    Access control:
    - All team members can view published events
    - Coordinators and admins can create/edit events
    - Only admins can delete events
    """

    title = models.CharField(_("title"), max_length=200)
    description = models.TextField(_("description"), blank=True)
    location = models.CharField(_("location"), max_length=300, blank=True)
    start_datetime = models.DateTimeField(_("start date/time"))
    end_datetime = models.DateTimeField(_("end date/time"))
    is_all_day = models.BooleanField(_("all day"), default=False)
    recurrence = RecurrenceField(_("recurrence"), blank=True, null=True)
    category = models.CharField(
        _("category"),
        max_length=20,
        choices=EventCategory.choices,
        default=EventCategory.OTHER,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("created by"),
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_events",
    )
    is_published = models.BooleanField(_("published"), default=True)

    # Custom queryset manager for date-range queries
    event_objects = EventQuerySet.as_manager()

    class Meta:
        ordering = ["start_datetime"]
        verbose_name = _("event")
        verbose_name_plural = _("events")

    def __str__(self) -> str:
        return self.title

    def get_absolute_url(self) -> str:
        return reverse("events:event_detail", args=[self.team.slug, self.pk])

    @property
    def slots_summary(self) -> str:
        """Return a summary like '3/5 slots filled'."""
        total_needed = sum(s.slots_needed for s in self.volunteer_slots.all())
        total_filled = sum(s.signups.exclude(status="cancelled").count() for s in self.volunteer_slots.all())
        return f"{total_filled}/{total_needed}"


class VolunteerSlot(BaseTeamModel):
    """
    A volunteer position within an event (e.g., "Nursery", "Ushers", "Food").

    Each slot specifies how many volunteers are needed. Members can sign up
    for available slots via VolunteerSignup.
    """

    event = models.ForeignKey(
        Event,
        verbose_name=_("event"),
        on_delete=models.CASCADE,
        related_name="volunteer_slots",
    )
    role_name = models.CharField(_("role name"), max_length=100)
    description = models.TextField(_("description"), blank=True)
    slots_needed = models.PositiveIntegerField(_("slots needed"), default=1)

    class Meta:
        ordering = ["role_name"]
        verbose_name = _("volunteer slot")
        verbose_name_plural = _("volunteer slots")

    def __str__(self) -> str:
        return f"{self.role_name} — {self.event.title}"

    @property
    def active_signups(self):
        """Return signups that are not cancelled."""
        return self.signups.exclude(status=SignupStatus.CANCELLED)

    @property
    def slots_remaining(self) -> int:
        """How many more volunteers are needed."""
        return max(0, self.slots_needed - self.active_signups.count())

    @property
    def is_full(self) -> bool:
        return self.slots_remaining == 0


class SignupStatus(models.TextChoices):
    """Status choices for volunteer signups."""

    CONFIRMED = "confirmed", _("Confirmed")
    TENTATIVE = "tentative", _("Tentative")
    CANCELLED = "cancelled", _("Cancelled")


class VolunteerSignup(BaseTeamModel):
    """
    A volunteer's sign-up for a specific slot.

    Each user can only sign up once per slot (enforced by unique_together).
    """

    slot = models.ForeignKey(
        VolunteerSlot,
        verbose_name=_("slot"),
        on_delete=models.CASCADE,
        related_name="signups",
    )
    volunteer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("volunteer"),
        on_delete=models.CASCADE,
        related_name="volunteer_signups",
    )
    note = models.TextField(_("note"), blank=True)
    status = models.CharField(
        _("status"),
        max_length=20,
        choices=SignupStatus.choices,
        default=SignupStatus.CONFIRMED,
    )

    class Meta:
        unique_together = ["slot", "volunteer"]
        verbose_name = _("volunteer signup")
        verbose_name_plural = _("volunteer signups")

    def __str__(self) -> str:
        return f"{self.volunteer} → {self.slot.role_name}"
