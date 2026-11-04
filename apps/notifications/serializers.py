"""Request and response serializers for notification APIs."""

from rest_framework import serializers

from .models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    notification_id = serializers.UUIDField(source="id", read_only=True)
    low_stock_alert = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = (
            "notification_id",
            "type",
            "status",
            "created_at",
            "low_stock_alert",
        )

    def get_low_stock_alert(self, instance):
        alert = getattr(instance, "stock_alert", None)
        if alert is None:
            return None
        return {
            "blood_group": alert.threshold.blood_group,
            "component": alert.threshold.component,
            "available_units": alert.available_units,
            "threshold_units": alert.threshold_units,
        }


class NotificationFailureSerializer(serializers.ModelSerializer):
    notification_id = serializers.UUIDField(source="id", read_only=True)
    code = serializers.CharField(source="failure_code", read_only=True)

    class Meta:
        model = Notification
        fields = ("notification_id", "code", "created_at")
