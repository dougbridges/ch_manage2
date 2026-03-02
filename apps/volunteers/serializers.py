"""
DRF serializers for the volunteers app.
"""

from rest_framework import serializers

from .models import ScheduledShift, VolunteerProfile


class VolunteerProfileSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source="user.get_display_name", read_only=True)
    user_email = serializers.EmailField(source="user.email", read_only=True)

    class Meta:
        model = VolunteerProfile
        fields = [
            "id",
            "user",
            "user_name",
            "user_email",
            "skills",
            "max_services_per_month",
            "is_active",
            "notes",
            "created_at",
        ]
        read_only_fields = ["id", "user", "user_name", "user_email", "created_at"]


class ScheduledShiftSerializer(serializers.ModelSerializer):
    schedule_name = serializers.CharField(source="schedule.name", read_only=True)
    volunteer_name = serializers.CharField(source="volunteer.user.get_display_name", read_only=True)
    event_title = serializers.CharField(source="event.title", read_only=True, default="")

    class Meta:
        model = ScheduledShift
        fields = [
            "id",
            "schedule",
            "schedule_name",
            "volunteer",
            "volunteer_name",
            "event",
            "event_title",
            "date",
            "status",
            "reminder_sent",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "schedule",
            "schedule_name",
            "volunteer",
            "volunteer_name",
            "event",
            "event_title",
            "date",
            "reminder_sent",
            "created_at",
        ]
