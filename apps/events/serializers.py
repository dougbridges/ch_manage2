"""
DRF serializers for the events app.
"""

from rest_framework import serializers

from .models import Event, VolunteerSignup, VolunteerSlot


class VolunteerSignupSerializer(serializers.ModelSerializer):
    volunteer_name = serializers.CharField(source="volunteer.get_display_name", read_only=True)

    class Meta:
        model = VolunteerSignup
        fields = ["id", "volunteer", "volunteer_name", "note", "status", "created_at"]
        read_only_fields = ["id", "volunteer", "volunteer_name", "status", "created_at"]


class VolunteerSlotSerializer(serializers.ModelSerializer):
    signups = VolunteerSignupSerializer(many=True, read_only=True)
    active_signups_count = serializers.SerializerMethodField()
    slots_remaining = serializers.IntegerField(read_only=True)

    class Meta:
        model = VolunteerSlot
        fields = [
            "id",
            "role_name",
            "description",
            "slots_needed",
            "active_signups_count",
            "slots_remaining",
            "signups",
        ]

    def get_active_signups_count(self, obj):
        return obj.active_signups.count()


class VolunteerSlotWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = VolunteerSlot
        fields = ["id", "role_name", "description", "slots_needed"]


class EventListSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source="created_by.get_display_name", read_only=True)

    class Meta:
        model = Event
        fields = [
            "id",
            "title",
            "description",
            "location",
            "start_datetime",
            "end_datetime",
            "is_all_day",
            "category",
            "is_published",
            "created_by",
            "created_by_name",
            "created_at",
        ]
        read_only_fields = ["id", "created_by", "created_by_name", "created_at"]


class EventDetailSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source="created_by.get_display_name", read_only=True)
    volunteer_slots = VolunteerSlotSerializer(many=True, read_only=True)
    slots_summary = serializers.CharField(read_only=True)

    class Meta:
        model = Event
        fields = [
            "id",
            "title",
            "description",
            "location",
            "start_datetime",
            "end_datetime",
            "is_all_day",
            "category",
            "is_published",
            "created_by",
            "created_by_name",
            "created_at",
            "volunteer_slots",
            "slots_summary",
        ]
        read_only_fields = ["id", "created_by", "created_by_name", "created_at"]


class EventWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Event
        fields = [
            "title",
            "description",
            "location",
            "start_datetime",
            "end_datetime",
            "is_all_day",
            "category",
            "is_published",
        ]

    def validate(self, data):
        if data.get("end_datetime") and data.get("start_datetime"):
            if data["end_datetime"] <= data["start_datetime"]:
                raise serializers.ValidationError({"end_datetime": "End must be after start."})
        return data
