"""
Forms for the volunteers app.

Covers volunteer profile editing, availability management,
and rotation schedule creation/editing.
"""

from django import forms
from django.utils.translation import gettext_lazy as _

from .models import RotationMembership, RotationSchedule, VolunteerProfile


class VolunteerProfileForm(forms.ModelForm):
    """Form for editing a volunteer's profile."""

    class Meta:
        model = VolunteerProfile
        fields = ["max_services_per_month", "is_active", "notes"]
        widgets = {
            "max_services_per_month": forms.NumberInput(attrs={"class": "input input-bordered w-full", "min": 1}),
            "notes": forms.Textarea(attrs={"class": "textarea textarea-bordered w-full", "rows": 3}),
        }


class RotationScheduleForm(forms.ModelForm):
    """Form for creating/editing a rotation schedule."""

    class Meta:
        model = RotationSchedule
        fields = ["name", "event", "slot_role_name", "rotation_strategy", "is_active"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "input input-bordered w-full"}),
            "event": forms.Select(attrs={"class": "select select-bordered w-full"}),
            "slot_role_name": forms.TextInput(attrs={"class": "input input-bordered w-full"}),
            "rotation_strategy": forms.Select(attrs={"class": "select select-bordered w-full"}),
        }

    def __init__(self, *args, team=None, **kwargs):
        super().__init__(*args, **kwargs)
        if team:
            from apps.events.models import Event
            self.fields["event"].queryset = Event.objects.filter(team=team)


class GenerateShiftsForm(forms.Form):
    """Form for generating rotation shifts over a date range."""

    start_date = forms.DateField(
        label=_("Start Date"),
        widget=forms.DateInput(attrs={"type": "date", "class": "input input-bordered w-full"}),
    )
    end_date = forms.DateField(
        label=_("End Date"),
        widget=forms.DateInput(attrs={"type": "date", "class": "input input-bordered w-full"}),
    )

    def clean(self):
        cleaned_data = super().clean()
        start = cleaned_data.get("start_date")
        end = cleaned_data.get("end_date")
        if start and end and end <= start:
            self.add_error("end_date", _("End date must be after start date."))
        return cleaned_data
