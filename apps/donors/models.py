"""Donor profiles and append-only completed donation records."""

from uuid import uuid4

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.utils import NotSupportedError


class AppendOnlyQuerySet(models.QuerySet):
    def update(self, **kwargs):
        raise NotSupportedError("Donation records are append-only.")

    def delete(self):
        raise NotSupportedError("Donation records are append-only.")


class DonorProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="donor_profile")
    birth_date = models.DateField()
    weight_kg = models.DecimalField(max_digits=5, decimal_places=2)
    blood_group = models.CharField(max_length=3)
    last_donation_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=models.Q(weight_kg__gte=0), name="donors_profile_weight_nonnegative"),
            models.CheckConstraint(condition=models.Q(blood_group__in=("O-", "O+", "A-", "A+", "B-", "B+", "AB-", "AB+")), name="donors_profile_blood_group_valid"),
        ]


class Donation(models.Model):
    class Component(models.TextChoices):
        WHOLE_BLOOD = "WHOLE_BLOOD", "Whole blood"
        RBC = "RBC", "Red blood cells"
        PLASMA = "PLASMA", "Plasma"
        PLATELETS = "PLATELETS", "Platelets"

    class Status(models.TextChoices):
        COMPLETED = "COMPLETED", "Completed"

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    donor = models.ForeignKey(DonorProfile, on_delete=models.PROTECT, related_name="donations")
    donation_date = models.DateField()
    blood_group = models.CharField(max_length=3)
    component = models.CharField(max_length=16, choices=Component.choices, default=Component.WHOLE_BLOOD)
    quantity_units = models.PositiveSmallIntegerField(default=1)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.COMPLETED)
    screening_weight_kg = models.DecimalField(max_digits=5, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = AppendOnlyQuerySet.as_manager()

    class Meta:
        ordering = ("-donation_date", "-created_at")
        constraints = [
            models.CheckConstraint(condition=models.Q(quantity_units__gte=1), name="donors_donation_units_positive"),
            models.CheckConstraint(condition=models.Q(screening_weight_kg__gte=0), name="donors_donation_weight_nonnegative"),
            models.CheckConstraint(condition=models.Q(status="COMPLETED"), name="donors_donation_completed_only"),
        ]

    def save(self, *args, **kwargs):
        if self.pk and type(self).objects.filter(pk=self.pk).exists():
            raise ValidationError("Donation records are append-only.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Donation records are append-only.")


class DonationSlot(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    starts_at = models.DateTimeField(db_index=True)
    capacity = models.PositiveSmallIntegerField(default=settings.DONATION_SLOT_CAPACITY)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("starts_at", "id")
        constraints = [
            models.CheckConstraint(condition=models.Q(capacity__gte=1), name="donors_slot_capacity_positive"),
        ]


class Appointment(models.Model):
    class Status(models.TextChoices):
        BOOKED = "BOOKED", "Booked"
        CANCELLED = "CANCELLED", "Cancelled"
        COMPLETED = "COMPLETED", "Completed"

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    donor = models.ForeignKey(DonorProfile, on_delete=models.PROTECT, related_name="appointments")
    slot = models.ForeignKey(DonationSlot, on_delete=models.PROTECT, related_name="appointments")
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.BOOKED)
    booked_at = models.DateTimeField(auto_now_add=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-slot__starts_at", "-booked_at")
        indexes = [models.Index(fields=("slot", "status"))]
