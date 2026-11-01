"""Blood request domain records."""

from uuid import uuid4

from django.conf import settings
from django.db import models


class BloodRequest(models.Model):
    """A recipient's validated request for blood components."""

    class Urgency(models.TextChoices):
        ROUTINE = "ROUTINE", "Routine"
        URGENT = "URGENT", "Urgent"
        EMERGENCY = "EMERGENCY", "Emergency"

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"
        ON_HOLD = "ON_HOLD", "On hold"
        RESERVED = "RESERVED", "Reserved"
        FULFILLED = "FULFILLED", "Fulfilled"

    BLOOD_GROUPS = ("O-", "O+", "A-", "A+", "B-", "B+", "AB-", "AB+")
    COMPONENTS = ("WHOLE_BLOOD", "RBC", "PLASMA", "PLATELETS")

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    request_id = models.CharField(max_length=25, unique=True, editable=False)
    requester = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="blood_requests",
    )
    patient_name = models.CharField(max_length=150)
    patient_blood_group = models.CharField(max_length=3)
    component = models.CharField(max_length=16)
    units_needed = models.PositiveIntegerField()
    urgency = models.CharField(max_length=9, choices=Urgency.choices)
    hospital = models.CharField(max_length=200)
    required_by = models.DateTimeField()
    contact_phone = models.CharField(max_length=16)
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.PENDING,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at", "request_id")
        constraints = [
            models.CheckConstraint(
                condition=models.Q(
                    patient_blood_group__in=(
                        "O-", "O+", "A-", "A+", "B-", "B+", "AB-", "AB+",
                    )
                ),
                name="request_patient_blood_group_valid",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    component__in=("WHOLE_BLOOD", "RBC", "PLASMA", "PLATELETS")
                ),
                name="request_component_valid",
            ),
            models.CheckConstraint(
                condition=models.Q(units_needed__gt=0),
                name="request_units_needed_positive",
            ),
            models.CheckConstraint(
                condition=models.Q(urgency__in=("ROUTINE", "URGENT", "EMERGENCY")),
                name="request_urgency_valid",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    status__in=(
                        "PENDING", "APPROVED", "REJECTED",
                        "ON_HOLD", "RESERVED", "FULFILLED",
                    )
                ),
                name="request_status_valid",
            ),
            models.CheckConstraint(
                condition=models.Q(required_by__gt=models.F("created_at")),
                name="request_required_by_after_creation",
            ),
        ]
