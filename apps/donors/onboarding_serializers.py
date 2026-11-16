"""Strict serializers for staff donor search and profile verification."""

from collections.abc import Mapping
from zoneinfo import ZoneInfo

from django.conf import settings
from django.utils import timezone
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from apps.core.validation import strict_json_type_errors


BLOOD_GROUPS = ("O-", "O+", "A-", "A+", "B-", "B+", "AB-", "AB+")


class StrictInputSerializer(serializers.Serializer):
    def to_internal_value(self, data):
        if isinstance(data, Mapping):
            errors = strict_json_type_errors(self.fields, data)
            if errors:
                raise ValidationError(errors)
        return super().to_internal_value(data)


class DonorLookupQuerySerializer(serializers.Serializer):
    q = serializers.CharField(min_length=2, max_length=100, trim_whitespace=True)


class DonorLookupSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    email = serializers.EmailField()
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    has_donor_profile = serializers.BooleanField()


class DonorProfileCreateSerializer(StrictInputSerializer):
    donor_id = serializers.IntegerField(min_value=1)
    birth_date = serializers.DateField()
    weight_kg = serializers.DecimalField(max_digits=5, decimal_places=2, min_value=0)
    blood_group = serializers.ChoiceField(choices=BLOOD_GROUPS)

    def validate_birth_date(self, value):
        zone = ZoneInfo(getattr(settings, "BLOOD_BANK_TIME_ZONE", "Asia/Kolkata"))
        today = timezone.now().astimezone(zone).date()
        if value > today:
            raise serializers.ValidationError("Birth date cannot be in the future.")
        return value


class DonorProfileResultSerializer(serializers.Serializer):
    donor_id = serializers.IntegerField(source="user_id", read_only=True)
    profile_status = serializers.SerializerMethodField()

    def get_profile_status(self, _profile):
        return "VERIFIED"
