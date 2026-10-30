"""Blood-unit inventory records."""

from uuid import uuid4

from django.db import models

from apps.donors.models import Donation


class BloodUnit(models.Model):
    """One tracked blood component unit linked to its completed donation."""

    class Component(models.TextChoices):
        WHOLE_BLOOD = "WHOLE_BLOOD", "Whole blood"
        RBC = "RBC", "Red blood cells"
        PLASMA = "PLASMA", "Plasma"
        PLATELETS = "PLATELETS", "Platelets"

    class Status(models.TextChoices):
        AVAILABLE = "AVAILABLE", "Available"
        RESERVED = "RESERVED", "Reserved"
        ISSUED = "ISSUED", "Issued"
        DISCARDED = "DISCARDED", "Discarded"
        RETURNED = "RETURNED", "Returned"
        EXPIRED = "EXPIRED", "Expired"

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    donation = models.ForeignKey(Donation, on_delete=models.PROTECT, related_name="blood_units")
    unit_code = models.CharField(max_length=64, unique=True)
    blood_group = models.CharField(max_length=3)
    component = models.CharField(max_length=16, choices=Component.choices)
    collected_at = models.DateTimeField()
    expiry_date = models.DateField()
    quantity_units = models.PositiveIntegerField()
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.AVAILABLE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at", "id")
        constraints = [
            models.CheckConstraint(
                condition=models.Q(blood_group__in=("O-", "O+", "A-", "A+", "B-", "B+", "AB-", "AB+")),
                name="inv_unit_blood_group_valid",
            ),
            models.CheckConstraint(
                condition=models.Q(component__in=("WHOLE_BLOOD", "RBC", "PLASMA", "PLATELETS")),
                name="inv_unit_component_valid",
            ),
            models.CheckConstraint(
                condition=models.Q(status__in=("AVAILABLE", "RESERVED", "ISSUED", "DISCARDED", "RETURNED", "EXPIRED")),
                name="inv_unit_status_valid",
            ),
            models.CheckConstraint(
                condition=models.Q(quantity_units__gt=0),
                name="inv_unit_quantity_positive",
            ),
            models.CheckConstraint(
                condition=models.Q(expiry_date__gt=models.F("collected_at__date")),
                name="inv_unit_expiry_after_collection",
            ),
        ]
