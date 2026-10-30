"""Request and response serializers for account APIs."""

import re
from collections.abc import Mapping

from django.contrib.auth.password_validation import validate_password
from rest_framework.exceptions import ValidationError
from rest_framework import serializers

from apps.core.validation import strict_json_type_errors

from .models import AccountRole, User
from .services import DuplicateAccountValue, PROFILE_WRITABLE_FIELDS, register_account


class StrictInputSerializer(serializers.Serializer):
    """Reject undeclared fields and invalid JSON value types."""

    def to_internal_value(self, data):
        if not isinstance(data, Mapping):
            return super().to_internal_value(data)

        errors = strict_json_type_errors(self.fields, data)

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


class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "email", "first_name", "last_name", "phone", "role")
        read_only_fields = ("id", "email", "role")

    def to_internal_value(self, data):
        if hasattr(data, "keys"):
            unknown = set(data.keys()) - set(self.fields)
            protected_fields = {
                "id",
                "email",
                "role",
                "is_active",
                "is_staff",
                "is_superuser",
                "password",
            }
            protected = set(data.keys()) & protected_fields
            user_role = getattr(self.instance, "role", None)
            writable = PROFILE_WRITABLE_FIELDS.get(user_role, frozenset())
            forbidden = (set(data.keys()) & set(self.fields)) - writable
            errors = {
                field: ["This profile field cannot be changed."]
                for field in protected | forbidden
            }
            if unknown:
                errors["non_field_errors"] = ["Unexpected profile fields are not allowed."]
            if errors:
                raise serializers.ValidationError(errors)
            for name in ("first_name", "last_name", "phone"):
                if name in data and not isinstance(data[name], str):
                    raise serializers.ValidationError({name: ["Not a valid string."]})
        return super().to_internal_value(data)

    def validate(self, attrs):
        if not attrs:
            raise serializers.ValidationError("At least one permitted profile field is required.")
        return attrs

    def get_fields(self):
        fields = super().get_fields()
        user = self.instance
        writable = PROFILE_WRITABLE_FIELDS.get(getattr(user, "role", None), frozenset())
        for name in ("first_name", "last_name", "phone"):
            fields[name].read_only = name not in writable
        fields["phone"].max_length = 16
        return fields

    def validate_phone(self, value):
        normalized = re.sub(r"[\s().-]", "", value)
        if not re.fullmatch(r"\+?[1-9][0-9]{6,14}", normalized):
            raise serializers.ValidationError("Enter a valid phone number.")
        if User.objects.filter(phone=normalized).exclude(pk=self.instance.pk).exists():
            raise serializers.ValidationError("An account with this phone already exists.")
        return normalized


class LoginSerializer(StrictInputSerializer):
    email = serializers.EmailField(max_length=254)
    password = serializers.CharField(write_only=True, trim_whitespace=False, max_length=128)

    def validate_email(self, value):
        return User.objects.normalize_email(value).casefold()


class EmptyRequestSerializer(StrictInputSerializer):
    """Validate endpoints that accept no request body fields."""
