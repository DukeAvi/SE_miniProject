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
    )
    type = models.CharField(max_length=32, choices=Type.choices)
    status = models.CharField(
        max_length=6,
        choices=Status.choices,
        default=Status.QUEUED,
    )
    created_at = models.DateTimeField(auto_now_add=True)

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
                    )
                ),
                name="notification_type_catalogued",
            ),
            models.CheckConstraint(
                condition=models.Q(status__in=("QUEUED", "SENT", "FAILED")),
                name="notification_status_valid",
            ),
        ]
