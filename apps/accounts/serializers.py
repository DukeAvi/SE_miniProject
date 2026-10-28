"""Request and response serializers for account APIs."""

import re
from collections.abc import Mapping

from django.contrib.auth.password_validation import validate_password
from rest_framework.exceptions import ValidationError
from rest_framework import serializers

from .models import AccountRole, User
from .services import DuplicateAccountValue, register_account


class StrictInputSerializer(serializers.Serializer):
    """Reject undeclared fields and non-string JSON values for text fields."""

    def to_internal_value(self, data):
        if not isinstance(data, Mapping):
            return super().to_internal_value(data)

        errors = {}
        unknown_fields = set(data) - set(self.fields)
        if unknown_fields:
            errors["non_field_errors"] = ["Unexpected fields are not allowed."]

        for field_name, field in self.fields.items():
            value = data.get(field_name)
            if (
                field_name in data
                and value is not None
                and isinstance(field, serializers.CharField)
                and not isinstance(value, str)
            ):
                errors[field_name] = ["Not a valid string."]

        if errors:
            raise ValidationError(errors)
        return super().to_internal_value(data)


class RegistrationSerializer(StrictInputSerializer):
    email = serializers.EmailField(max_length=254)
    first_name = serializers.CharField(max_length=150, trim_whitespace=True)
    last_name = serializers.CharField(max_length=150, trim_whitespace=True)
    phone = serializers.CharField(max_length=32, trim_whitespace=True)
    password = serializers.CharField(write_only=True, trim_whitespace=False, max_length=128)
    role = serializers.ChoiceField(choices=(AccountRole.DONOR, AccountRole.RECIPIENT))

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

    def create(self, validated_data):
        try:
            return register_account(**validated_data)
        except DuplicateAccountValue as error:
            raise serializers.ValidationError(
                {error.field: [f"An account with this {error.field} already exists."]}
            ) from error


class UserPublicSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "email", "first_name", "last_name", "phone", "role")


class LoginSerializer(StrictInputSerializer):
    email = serializers.EmailField(max_length=254)
    password = serializers.CharField(write_only=True, trim_whitespace=False, max_length=128)

    def validate_email(self, value):
        return User.objects.normalize_email(value).casefold()


class EmptyRequestSerializer(StrictInputSerializer):
    """Validate endpoints that accept no request body fields."""
