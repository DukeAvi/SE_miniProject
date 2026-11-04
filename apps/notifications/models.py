"""Durable notification outbox records."""

from uuid import uuid4

from django.conf import settings
from django.db import models


class Notification(models.Model):
    """A queued user notification created with its triggering transaction."""

    class Type(models.TextChoices):
        REQUEST_APPROVED = "REQUEST_APPROVED", "Request approved"
        REQUEST_REJECTED = "REQUEST_REJECTED", "Request rejected"
        REQUEST_HELD = "REQUEST_HELD", "Request held"
        REQUEST_RESERVED = "REQUEST_RESERVED", "Request reserved"
        REQUEST_FULFILLED = "REQUEST_FULFILLED", "Request fulfilled"
        LOW_STOCK_ALERT = "LOW_STOCK_ALERT", "Low stock alert"

    class Status(models.TextChoices):
        QUEUED = "QUEUED", "Queued"
        SENT = "SENT", "Sent"
        FAILED = "FAILED", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="notifications",
    )
    blood_request = models.ForeignKey(
        "requests.BloodRequest",
        on_delete=models.PROTECT,
        related_name="notification_outbox",
        null=True,
        blank=True,
    )
    stock_alert = models.ForeignKey(
        "inventory.LowStockAlert",
        on_delete=models.PROTECT,
        related_name="notifications",
        null=True,
        blank=True,
    )
    type = models.CharField(max_length=32, choices=Type.choices)
    status = models.CharField(
        max_length=6,
        choices=Status.choices,
        default=Status.QUEUED,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    attempt_count = models.PositiveSmallIntegerField(default=0)
    next_attempt_at = models.DateTimeField(null=True, blank=True)
    last_attempt_at = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    failure_code = models.CharField(max_length=64, blank=True, default="")

    class Meta:
        ordering = ("created_at", "id")
        indexes = [
            models.Index(
                fields=("status", "created_at"),
                name="notification_status_time_idx",
            ),
            models.Index(
                fields=("recipient", "created_at"),
                name="notice_recipient_time_idx",
            ),
            models.Index(
                fields=("status", "next_attempt_at"),
                name="notice_due_delivery_idx",
            ),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(
                    type__in=(
                        "REQUEST_APPROVED",
                        "REQUEST_REJECTED",
                        "REQUEST_HELD",
                        "REQUEST_RESERVED",
                        "REQUEST_FULFILLED",
                        "LOW_STOCK_ALERT",
                    )
                ),
                name="notification_type_catalogued",
            ),
            models.CheckConstraint(
                condition=models.Q(status__in=("QUEUED", "SENT", "FAILED")),
                name="notification_status_valid",
            ),
            models.CheckConstraint(
                condition=models.Q(attempt_count__lte=5),
                name="notification_attempts_max_five",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(
                        status="QUEUED",
                        sent_at__isnull=True,
                        failure_code="",
                    )
                    | models.Q(
                        status="SENT",
                        sent_at__isnull=False,
                        next_attempt_at__isnull=True,
                        failure_code="",
                    )
                    | models.Q(
                        status="FAILED",
                        sent_at__isnull=True,
                        next_attempt_at__isnull=True,
                    ) & ~models.Q(failure_code="")
                ),
                name="notification_delivery_metadata_matches_status",
            ),
            models.UniqueConstraint(
                fields=("blood_request", "type"),
                condition=models.Q(blood_request__isnull=False),
                name="notification_request_type_once",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(blood_request__isnull=False, stock_alert__isnull=True)
                    | models.Q(blood_request__isnull=True, stock_alert__isnull=False)
                ),
                name="notification_exactly_one_source",
            ),
            models.UniqueConstraint(
                fields=("stock_alert", "recipient"),
                condition=models.Q(stock_alert__isnull=False),
                name="notification_stock_alert_recipient_once",
            ),
        ]
