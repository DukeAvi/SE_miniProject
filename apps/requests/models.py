"""Blood request domain records."""

from uuid import uuid4

from django.conf import settings
from django.db import models

from apps.inventory.models import BloodUnit


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
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="reviewed_blood_requests",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    decision_reason = models.CharField(max_length=500, blank=True, default="")
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
            models.CheckConstraint(
                condition=(
                    models.Q(
                        status="PENDING",
                        reviewer__isnull=True,
                        reviewed_at__isnull=True,
                        decision_reason="",
                    )
                    | (
                        ~models.Q(status="PENDING")
                        & models.Q(reviewer__isnull=False, reviewed_at__isnull=False)
                    )
                ),
                name="request_review_metadata_matches_status",
            ),
            models.CheckConstraint(
                condition=(
                    ~models.Q(status__in=("REJECTED", "ON_HOLD"))
                    | ~models.Q(decision_reason="")
                ),
                name="request_reject_hold_reason_required",
            ),
        ]


class BloodAllocation(models.Model):
    """A request's active reservation or completed issue of one blood unit."""

    class Status(models.TextChoices):
        RESERVED = "RESERVED", "Reserved"
        ISSUED = "ISSUED", "Issued"
        RELEASED = "RELEASED", "Released"

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    blood_request = models.ForeignKey(
        BloodRequest,
        on_delete=models.PROTECT,
        related_name="allocations",
    )
    blood_unit = models.ForeignKey(
        BloodUnit,
        on_delete=models.PROTECT,
        related_name="allocations",
    )
    status = models.CharField(max_length=8, choices=Status.choices)
    allocated_at = models.DateTimeField(auto_now_add=True)
    issued_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("allocated_at", "id")
        constraints = [
            models.UniqueConstraint(
                fields=("blood_unit",),
                condition=models.Q(status__in=("RESERVED", "ISSUED")),
                name="requests_one_active_allocation_per_unit",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(status="RESERVED", issued_at__isnull=True)
                    | models.Q(status="ISSUED", issued_at__isnull=False)
                    | models.Q(status="RELEASED")
                ),
                name="requests_allocation_issue_timestamp_matches_status",
            ),
        ]


class IssueIdempotency(models.Model):
    """Persist successful issue responses so clients can safely retry."""

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    blood_request = models.ForeignKey(
        BloodRequest,
        on_delete=models.PROTECT,
        related_name="issue_idempotency_records",
    )
    key = models.CharField(max_length=128)
    response_body = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=~models.Q(key=""),
                name="requests_issue_idempotency_key_nonempty",
            ),
            models.UniqueConstraint(
                fields=("blood_request", "key"),
                name="requests_issue_idempotency_unique",
            ),
        ]
