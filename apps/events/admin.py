"""
Django admin registration for event models.
"""

from django.contrib import admin

from .models import Event, VolunteerSignup, VolunteerSlot


class VolunteerSlotInline(admin.TabularInline):
    model = VolunteerSlot
    extra = 1


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ("title", "team", "category", "start_datetime", "is_published")
    list_filter = ("category", "is_published", "team")
    search_fields = ("title",)
    inlines = [VolunteerSlotInline]


@admin.register(VolunteerSlot)
class VolunteerSlotAdmin(admin.ModelAdmin):
    list_display = ("role_name", "event", "team", "slots_needed")
    list_filter = ("team",)


@admin.register(VolunteerSignup)
class VolunteerSignupAdmin(admin.ModelAdmin):
    list_display = ("volunteer", "slot", "status", "team")
    list_filter = ("status", "team")
