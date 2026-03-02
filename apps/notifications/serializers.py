"""
DRF serializers for the notifications app.
"""

from rest_framework import serializers

from .models import MessageBlast, MessageRecipient


class MessageRecipientSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source="user.get_display_name", read_only=True)

    class Meta:
        model = MessageRecipient
        fields = ["id", "user", "user_name", "channel", "status", "sent_at", "error_message"]
        read_only_fields = ["id", "user", "user_name", "status", "sent_at", "error_message"]


class MessageBlastListSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source="created_by.get_display_name", read_only=True)
    recipient_count = serializers.IntegerField(read_only=True)
    sent_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = MessageBlast
        fields = [
            "id",
            "subject",
            "body",
            "channel",
            "status",
            "send_at",
            "sent_at",
            "created_by",
            "created_by_name",
            "recipient_count",
            "sent_count",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "status",
            "sent_at",
            "created_by",
            "created_by_name",
            "recipient_count",
            "sent_count",
            "created_at",
        ]


class MessageBlastDetailSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source="created_by.get_display_name", read_only=True)
    recipients = MessageRecipientSerializer(many=True, read_only=True)

    class Meta:
        model = MessageBlast
        fields = [
            "id",
            "subject",
            "body",
            "channel",
            "status",
            "send_at",
            "sent_at",
            "created_by",
            "created_by_name",
            "recipient_filter",
            "recipients",
            "created_at",
        ]
        read_only_fields = ["id", "status", "sent_at", "created_by", "created_by_name", "recipients", "created_at"]


class MessageBlastWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = MessageBlast
        fields = ["subject", "body", "channel", "send_at"]

    def validate(self, data):
        if data.get("channel") == "email" and not data.get("subject"):
            raise serializers.ValidationError({"subject": "Subject is required for email blasts."})
        return data
