"""
Django admin registration for notification models.
"""

from django.contrib import admin

from .models import ContactPreference, MessageBlast, MessageRecipient


class MessageRecipientInline(admin.TabularInline):
    model = MessageRecipient
    extra = 0
    readonly_fields = ("sent_at", "external_id", "error_message")


@admin.register(MessageBlast)
class MessageBlastAdmin(admin.ModelAdmin):
    list_display = ("__str__", "team", "channel", "status", "created_at")
    list_filter = ("channel", "status", "team")
    search_fields = ("subject",)
    date_hierarchy = "created_at"
    inlines = [MessageRecipientInline]


@admin.register(MessageRecipient)
class MessageRecipientAdmin(admin.ModelAdmin):
    list_display = ("user", "blast", "channel", "status", "sent_at")
    list_filter = ("status", "channel")
    search_fields = ("user__first_name", "user__last_name", "user__email")


@admin.register(ContactPreference)
class ContactPreferenceAdmin(admin.ModelAdmin):
    list_display = ("user", "team", "receive_email", "receive_sms", "phone_number")
    list_filter = ("team", "receive_email", "receive_sms")
    search_fields = ("user__first_name", "user__last_name", "user__email")
