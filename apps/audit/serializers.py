"""Request and response serializers for audit APIs."""

import re

from rest_framework import serializers

from .models import AuditEvent


class AuditSearchSerializer(serializers.Serializer):
    actor = serializers.IntegerField(min_value=1, required=False)
    action = serializers.ChoiceField(choices=AuditEvent.Action.choices, required=False)
    from_date = serializers.DateField(required=False)
    to_date = serializers.DateField(required=False)
    entity_type = serializers.CharField(max_length=64, required=False)
    entity_id = serializers.CharField(max_length=64, required=False)
    page = serializers.IntegerField(min_value=1, required=False)
    page_size = serializers.IntegerField(min_value=1, max_value=100, required=False)

    def validate_entity_type(self, value):
        if not re.fullmatch(r"[A-Z][A-Z0-9_]{0,63}", value):
            raise serializers.ValidationError("Use an uppercase audit entity type.")
        return value

    def validate_entity_id(self, value):
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", value):
            raise serializers.ValidationError("Enter a valid record identifier.")
        return value

    def validate(self, attrs):
        if ("entity_type" in attrs) != ("entity_id" in attrs):
            raise serializers.ValidationError(
                "entity_type and entity_id must be supplied together."
            )
        if (
            attrs.get("from_date") is not None
            and attrs.get("to_date") is not None
            and attrs["from_date"] > attrs["to_date"]
        ):
            raise serializers.ValidationError("from must not be after to.")
        return attrs


class AuditEventSerializer(serializers.ModelSerializer):
    actor_id = serializers.CharField(allow_null=True, read_only=True)
    created_at = serializers.DateTimeField(source="occurred_at", read_only=True)

    class Meta:
        model = AuditEvent
        fields = (
            "actor_id",
            "actor_role",
            "action",
            "entity_type",
            "entity_id",
            "outcome",
            "ip_address",
            "correlation_id",
            "created_at",
        )
