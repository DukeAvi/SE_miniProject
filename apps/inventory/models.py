"""Blood-unit inventory records."""

from uuid import uuid4

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.utils import NotSupportedError

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


class InventoryTransactionQuerySet(models.QuerySet):
    def update(self, **kwargs):
        raise NotSupportedError("Inventory transactions are append-only.")

    def delete(self):
        raise NotSupportedError("Inventory transactions are append-only.")


class InventoryTransaction(models.Model):
    """Append-only record of a stock-changing blood-unit transition."""

    class Action(models.TextChoices):
        RESERVE = "RESERVE", "Reserve"
        RELEASE = "RELEASE", "Release"
        ISSUE = "ISSUE", "Issue"
        EXPIRE = "EXPIRE", "Expire"
        DISCARD = "DISCARD", "Discard"
        RETURN = "RETURN", "Return"

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    blood_unit = models.ForeignKey(BloodUnit, on_delete=models.PROTECT, related_name="transactions")
    action = models.CharField(max_length=8, choices=Action.choices)
    from_status = models.CharField(max_length=12, choices=BloodUnit.Status.choices)
    to_status = models.CharField(max_length=12, choices=BloodUnit.Status.choices)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="inventory_transactions",
    )
    reason = models.CharField(max_length=500)
    occurred_at = models.DateTimeField(auto_now_add=True, db_index=True)

    objects = InventoryTransactionQuerySet.as_manager()

    class Meta:
        ordering = ("occurred_at", "id")
        constraints = [
            models.CheckConstraint(
                condition=models.Q(action__in=("RESERVE", "RELEASE", "ISSUE", "EXPIRE", "DISCARD", "RETURN")),
                name="inv_txn_action_valid",
            ),
            models.CheckConstraint(
                condition=models.Q(from_status__in=("AVAILABLE", "RESERVED", "ISSUED", "DISCARDED", "RETURNED", "EXPIRED")),
                name="inv_txn_from_status_valid",
            ),
            models.CheckConstraint(
                condition=models.Q(to_status__in=("AVAILABLE", "RESERVED", "ISSUED", "DISCARDED", "RETURNED", "EXPIRED")),
                name="inv_txn_to_status_valid",
            ),
        ]

    def save(self, *args, **kwargs):
        if self.pk and type(self).objects.filter(pk=self.pk).exists():
            raise ValidationError("Inventory transactions are append-only.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Inventory transactions are append-only.")
