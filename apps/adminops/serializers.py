"""Request and response serializers for administration APIs."""

from collections.abc import Mapping
import re

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from apps.accounts.models import AccountRole
from apps.core.validation import strict_json_type_errors


User = get_user_model()
MANAGED_ROLES = (AccountRole.STAFF, AccountRole.ADMIN)


class StrictInputSerializer(serializers.Serializer):
    def to_internal_value(self, data):
        if isinstance(data, Mapping):
            errors = strict_json_type_errors(self.fields, data)
            if errors:
                raise ValidationError(errors)
        return super().to_internal_value(data)


class ManagedUserCreateSerializer(StrictInputSerializer):
    email = serializers.EmailField(max_length=254)
    first_name = serializers.CharField(max_length=150, trim_whitespace=True)
    last_name = serializers.CharField(max_length=150, trim_whitespace=True)
    phone = serializers.CharField(max_length=16, trim_whitespace=True)
    password = serializers.CharField(write_only=True, max_length=128, trim_whitespace=False)
    role = serializers.ChoiceField(choices=MANAGED_ROLES)

    def validate_email(self, value):
        normalized = User.objects.normalize_email(value).casefold()
        if User.objects.filter(email__iexact=normalized).exists():
            raise serializers.ValidationError("An account with this email already exists.")
        return normalized

    def validate_phone(self, value):
        normalized = re.sub(r"[\s().-]", "", value)
        if not re.fullmatch(r"\+?[1-9][0-9]{6,14}", normalized):
            raise serializers.ValidationError("Enter a valid phone number.")
        if User.objects.filter(phone=normalized).exists():
            raise serializers.ValidationError("An account with this phone already exists.")
        return normalized

    def validate_password(self, value):
        validate_password(value)
        return value


class ManagedUserPatchSerializer(StrictInputSerializer):
    is_active = serializers.BooleanField(required=False)
    role = serializers.ChoiceField(choices=MANAGED_ROLES, required=False)

    def validate(self, attrs):
        if not attrs:
            raise serializers.ValidationError("At least one managed field is required.")
        return attrs


class ManagedUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "email", "first_name", "last_name", "phone", "role")
