"""Request and response serializers for inventory APIs."""

from collections.abc import Mapping
import re

from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from .models import BloodUnit


class StrictInputSerializer(serializers.Serializer):
    def to_internal_value(self, data):
        if isinstance(data, Mapping):
            if set(data) - set(self.fields):
                raise ValidationError({"non_field_errors": ["Unexpected fields are not allowed."]})
            for name, field in self.fields.items():
                if name in data and isinstance(field, serializers.CharField) and not isinstance(data[name], str):
                    raise ValidationError({name: ["Not a valid string."]})
        return super().to_internal_value(data)


class BloodUnitCreateSerializer(StrictInputSerializer):
    unit_code = serializers.CharField(max_length=64, trim_whitespace=True)
    donation_id = serializers.UUIDField()
    blood_group = serializers.ChoiceField(choices=("O-", "O+", "A-", "A+", "B-", "B+", "AB-", "AB+"))
    component = serializers.ChoiceField(choices=BloodUnit.Component.choices)
    collected_at = serializers.DateTimeField()
    expiry_date = serializers.DateField()
    quantity_units = serializers.IntegerField(min_value=1)

    def validate_unit_code(self, value):
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9-]{0,63}", value):
            raise serializers.ValidationError("Use letters, digits, and hyphens; start with a letter or digit.")
        return value.upper()


class BloodUnitTransitionSerializer(StrictInputSerializer):
    reason = serializers.CharField(max_length=500, trim_whitespace=True)


class BloodUnitSerializer(serializers.ModelSerializer):
    donation_id = serializers.UUIDField(read_only=True)

    class Meta:
        model = BloodUnit
        fields = (
            "id", "unit_code", "donation_id", "blood_group", "component",
            "status", "collected_at", "expiry_date", "quantity_units",
        )
