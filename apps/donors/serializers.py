"""Request and response serializers for donor APIs."""

from collections.abc import Mapping

from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from .models import Donation


class StrictInputSerializer(serializers.Serializer):
    def to_internal_value(self, data):
        if isinstance(data, Mapping):
            if set(data) - set(self.fields):
                raise ValidationError({"non_field_errors": ["Unexpected fields are not allowed."]})
            for name, field in self.fields.items():
                if name in data and isinstance(field, serializers.CharField) and not isinstance(data[name], str):
                    raise ValidationError({name: ["Not a valid string."]})
        return super().to_internal_value(data)


class DonationCreateSerializer(StrictInputSerializer):
    donor_id = serializers.IntegerField(min_value=1)
    donation_date = serializers.DateField()
    blood_group = serializers.ChoiceField(choices=("O-", "O+", "A-", "A+", "B-", "B+", "AB-", "AB+"))
    component = serializers.ChoiceField(choices=(Donation.Component.WHOLE_BLOOD,))
    quantity_units = serializers.IntegerField(min_value=1, max_value=20)
    status = serializers.ChoiceField(choices=(Donation.Status.COMPLETED,))
    screening_weight_kg = serializers.DecimalField(max_digits=5, decimal_places=2, min_value=0)


class DonationSerializer(serializers.ModelSerializer):
    donor_id = serializers.IntegerField(source="donor.user_id", read_only=True)

    class Meta:
        model = Donation
        fields = ("id", "donor_id", "donation_date", "blood_group", "component", "quantity_units", "status", "screening_weight_kg", "created_at")
