"""Strict JSON input type checks shared by request serializers."""

from collections.abc import Mapping

from rest_framework import serializers


def strict_json_type_errors(fields, data):
    if not isinstance(data, Mapping):
        return {}
    errors = {}
    if set(data) - set(fields):
        errors["non_field_errors"] = ["Unexpected fields are not allowed."]
    for name, field in fields.items():
        if name not in data or data[name] is None:
            continue
        value = data[name]
        if isinstance(field, serializers.IntegerField):
            valid = type(value) is int
            message = "Not a valid integer."
        elif isinstance(field, serializers.DecimalField):
            valid = not isinstance(value, bool) and isinstance(value, (int, float, str))
            message = "Not a valid decimal."
        elif isinstance(field, (serializers.CharField, serializers.ChoiceField,
                                serializers.UUIDField, serializers.DateField, serializers.DateTimeField)):
            valid = isinstance(value, str)
            message = "Not a valid string."
        else:
            continue
        if not valid:
            errors[name] = [message]
    return errors
