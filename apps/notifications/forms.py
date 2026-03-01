"""
Forms for the notifications app.

BlastComposeForm handles creating a new message blast.
ContactPreferenceForm handles user notification preferences.
"""

from django import forms
from django.utils.translation import gettext_lazy as _

from .models import ContactPreference, MessageBlast


class BlastComposeForm(forms.ModelForm):
    """
    Form for composing a new message blast.

    The team and created_by fields are set in the view.
    """

    class Meta:
        model = MessageBlast
        fields = ["subject", "body", "channel", "send_at"]
        widgets = {
            "subject": forms.TextInput(attrs={"class": "input input-bordered w-full"}),
            "body": forms.Textarea(attrs={"class": "textarea textarea-bordered w-full", "rows": 6}),
            "channel": forms.Select(attrs={"class": "select select-bordered w-full"}),
            "send_at": forms.DateTimeInput(
                attrs={"type": "datetime-local", "class": "input input-bordered w-full"},
            ),
        }

    def clean(self):
        cleaned_data = super().clean()
        channel = cleaned_data.get("channel")
        subject = cleaned_data.get("subject")
        # Email blasts require a subject
        if channel == "email" and not subject:
            self.add_error("subject", _("Subject is required for email blasts."))
        return cleaned_data


class ContactPreferenceForm(forms.ModelForm):
    """
    Form for editing a user's notification preferences.

    The team and user fields are set in the view.
    """

    class Meta:
        model = ContactPreference
        fields = ["phone_number", "receive_email", "receive_sms"]
        widgets = {
            "phone_number": forms.TextInput(
                attrs={"class": "input input-bordered w-full", "placeholder": "+15551234567"},
            ),
        }

    def clean(self):
        cleaned_data = super().clean()
        receive_sms = cleaned_data.get("receive_sms")
        phone_number = cleaned_data.get("phone_number")
        if receive_sms and not phone_number:
            self.add_error("phone_number", _("Phone number is required to receive SMS notifications."))
        return cleaned_data
