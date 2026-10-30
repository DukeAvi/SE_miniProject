"""Request and response serializers for donor APIs."""

from collections.abc import Mapping

from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from apps.core.validation import strict_json_type_errors

from .models import Appointment, Donation, DonationSlot


class StrictInputSerializer(serializers.Serializer):
    def to_internal_value(self, data):
        if isinstance(data, Mapping):
            errors = strict_json_type_errors(self.fields, data)
            if errors:
                raise ValidationError(errors)
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


class AppointmentCreateSerializer(StrictInputSerializer):
    slot_id = serializers.UUIDField()


class AppointmentSerializer(serializers.ModelSerializer):
    appointment_id = serializers.UUIDField(source="id", read_only=True)
    slot_id = serializers.UUIDField(read_only=True)
    starts_at = serializers.DateTimeField(source="slot.starts_at", read_only=True)

    class Meta:
        model = Appointment
        fields = ("appointment_id", "slot_id", "starts_at", "status")


class DonationSlotSerializer(serializers.ModelSerializer):
    slot_id = serializers.UUIDField(source="id", read_only=True)
    available_capacity = serializers.SerializerMethodField()

    def get_available_capacity(self, obj):
        return max(0, obj.capacity - getattr(obj, "active_bookings", 0))

    class Meta:
        model = DonationSlot
        fields = ("slot_id", "starts_at", "capacity", "available_capacity")
