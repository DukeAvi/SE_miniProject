"""Request and response serializers for notification APIs."""

from rest_framework import serializers

from .models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    notification_id = serializers.UUIDField(source="id", read_only=True)

    class Meta:
        model = Notification
        fields = ("notification_id", "type", "status", "created_at")


class NotificationFailureSerializer(serializers.ModelSerializer):
    notification_id = serializers.UUIDField(source="id", read_only=True)
    code = serializers.CharField(source="failure_code", read_only=True)

    class Meta:
        model = Notification
        fields = ("notification_id", "code", "created_at")
