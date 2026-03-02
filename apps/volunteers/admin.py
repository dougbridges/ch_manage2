"""
Django admin registration for volunteer models.
"""

from django.contrib import admin

from .models import Availability, RotationMembership, RotationSchedule, ScheduledShift, VolunteerProfile


class AvailabilityInline(admin.TabularInline):
    model = Availability
    extra = 0


class RotationMembershipInline(admin.TabularInline):
    model = RotationMembership
    extra = 0


@admin.register(VolunteerProfile)
class VolunteerProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "team", "is_active", "max_services_per_month")
    list_filter = ("team", "is_active")
    inlines = [AvailabilityInline]


@admin.register(Availability)
class AvailabilityAdmin(admin.ModelAdmin):
    list_display = ("volunteer", "date", "is_available")
    list_filter = ("is_available",)


@admin.register(RotationSchedule)
class RotationScheduleAdmin(admin.ModelAdmin):
    list_display = ("name", "team", "rotation_strategy", "is_active")
    list_filter = ("team", "rotation_strategy", "is_active")
    inlines = [RotationMembershipInline]


@admin.register(ScheduledShift)
class ScheduledShiftAdmin(admin.ModelAdmin):
    list_display = ("volunteer", "schedule", "date", "status", "reminder_sent")
    list_filter = ("status", "reminder_sent")
