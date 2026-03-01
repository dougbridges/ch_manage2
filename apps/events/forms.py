"""
Forms for the events app.

EventForm handles creation/editing of events. VolunteerSlotForm handles
creation/editing of volunteer slots within an event.
"""

from django import forms
from django.utils.translation import gettext_lazy as _

from .models import Event, VolunteerSlot


class EventForm(forms.ModelForm):
    """
    Form for creating and editing events.

    The team and created_by fields are set in the view, not in the form.
    """

    class Meta:
        model = Event
        fields = [
            "title",
            "description",
            "location",
            "start_datetime",
            "end_datetime",
            "is_all_day",
            "recurrence",
            "category",
            "is_published",
        ]
        widgets = {
            "start_datetime": forms.DateTimeInput(
                attrs={"type": "datetime-local", "class": "input input-bordered w-full"},
            ),
            "end_datetime": forms.DateTimeInput(
                attrs={"type": "datetime-local", "class": "input input-bordered w-full"},
            ),
            "title": forms.TextInput(attrs={"class": "input input-bordered w-full"}),
            "location": forms.TextInput(attrs={"class": "input input-bordered w-full"}),
            "description": forms.Textarea(attrs={"class": "textarea textarea-bordered w-full", "rows": 4}),
            "category": forms.Select(attrs={"class": "select select-bordered w-full"}),
        }

    def clean(self):
        cleaned_data = super().clean()
        start = cleaned_data.get("start_datetime")
        end = cleaned_data.get("end_datetime")
        if start and end and end <= start:
            raise forms.ValidationError(_("End date/time must be after start date/time."))
        return cleaned_data


class VolunteerSlotForm(forms.ModelForm):
    """
    Form for creating and editing volunteer slots.

    The event and team fields are set in the view.
    """

    class Meta:
        model = VolunteerSlot
        fields = ["role_name", "description", "slots_needed"]
        widgets = {
            "role_name": forms.TextInput(attrs={"class": "input input-bordered w-full"}),
            "description": forms.Textarea(attrs={"class": "textarea textarea-bordered w-full", "rows": 3}),
            "slots_needed": forms.NumberInput(attrs={"class": "input input-bordered w-full", "min": 1}),
        }
