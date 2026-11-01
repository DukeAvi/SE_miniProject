"""Request and response serializers for blood request APIs."""

from collections.abc import Mapping
import re

from django.utils import timezone
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from apps.core.validation import strict_json_type_errors

from .models import BloodRequest


class StrictInputSerializer(serializers.Serializer):
    def to_internal_value(self, data):
        if isinstance(data, Mapping):
            errors = strict_json_type_errors(self.fields, data)
            if errors:
                raise ValidationError(errors)
        return super().to_internal_value(data)


class BloodRequestCreateSerializer(StrictInputSerializer):
    patient_name = serializers.CharField(max_length=150, trim_whitespace=True)
    patient_blood_group = serializers.ChoiceField(choices=BloodRequest.BLOOD_GROUPS)
    component = serializers.ChoiceField(choices=BloodRequest.COMPONENTS)
    units_needed = serializers.IntegerField(min_value=1)
    urgency = serializers.ChoiceField(choices=BloodRequest.Urgency.choices)
    hospital = serializers.CharField(max_length=200, trim_whitespace=True)
    required_by = serializers.DateTimeField()
    contact_phone = serializers.CharField(max_length=16, trim_whitespace=True)

    def validate_required_by(self, value):
        if value <= timezone.now():
            raise serializers.ValidationError("Must be in the future.")
        return value

    def validate_contact_phone(self, value):
        normalized = re.sub(r"[\s().-]", "", value)
        if not re.fullmatch(r"\+?[1-9][0-9]{6,14}", normalized):
            raise serializers.ValidationError("Enter a valid phone number.")
        return normalized


class BloodRequestDecisionSerializer(StrictInputSerializer):
    decision = serializers.ChoiceField(choices=("APPROVE", "REJECT", "HOLD"))
    reason = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=500,
        trim_whitespace=True,
    )


class BloodRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = BloodRequest
        fields = (
            "request_id",
            "patient_blood_group",
            "component",
            "units_needed",
            "urgency",
            "status",
            "created_at",
        )
