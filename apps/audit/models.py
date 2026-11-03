from uuid import uuid4

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.utils import NotSupportedError


class AppendOnlyQuerySet(models.QuerySet):
    def update(self, **kwargs):
        raise NotSupportedError("Audit events are append-only.")

    def delete(self):
        raise NotSupportedError("Audit events are append-only.")


class AuditEvent(models.Model):
    class Action(models.TextChoices):
        LOGIN_SUCCESS = "LOGIN_SUCCESS", "Login success"
        LOGIN_FAILED = "LOGIN_FAILED", "Login failed"
        SESSION_EXPIRED = "SESSION_EXPIRED", "Session expired"
        USER_CREATED = "USER_CREATED", "User created"
        USER_DISABLED = "USER_DISABLED", "User disabled"
        USER_ENABLED = "USER_ENABLED", "User enabled"
        ROLE_CHANGED = "ROLE_CHANGED", "Role changed"
        DONOR_UPDATED = "DONOR_UPDATED", "Donor updated"
        APPOINTMENT_BOOKED = "APPOINTMENT_BOOKED", "Appointment booked"
        APPOINTMENT_CANCELLED = "APPOINTMENT_CANCELLED", "Appointment cancelled"
        DONATION_RECORDED = "DONATION_RECORDED", "Donation recorded"
        UNIT_CREATED = "UNIT_CREATED", "Unit created"
        UNIT_RESERVED = "UNIT_RESERVED", "Unit reserved"
        UNIT_RELEASED = "UNIT_RELEASED", "Unit released"
        UNIT_ISSUED = "UNIT_ISSUED", "Unit issued"
        UNIT_EXPIRED = "UNIT_EXPIRED", "Unit expired"
        UNIT_DISCARDED = "UNIT_DISCARDED", "Unit discarded"
        UNIT_RETURNED = "UNIT_RETURNED", "Unit returned"
        REQUEST_SUBMITTED = "REQUEST_SUBMITTED", "Request submitted"
        REQUEST_APPROVED = "REQUEST_APPROVED", "Request approved"
        REQUEST_RESERVED = "REQUEST_RESERVED", "Request reserved"
        REQUEST_REJECTED = "REQUEST_REJECTED", "Request rejected"
        REQUEST_HELD = "REQUEST_HELD", "Request held"
        REQUEST_FULFILLED = "REQUEST_FULFILLED", "Request fulfilled"
        THRESHOLD_CHANGED = "THRESHOLD_CHANGED", "Threshold changed"
        ACCESS_DENIED = "ACCESS_DENIED", "Access denied"

    class Outcome(models.TextChoices):
        SUCCESS = "SUCCESS", "Success"
        FAILURE = "FAILURE", "Failure"

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="audit_events",
    )
    action = models.CharField(max_length=64, choices=Action.choices, db_index=True)
    actor_role = models.CharField(max_length=10, null=True, blank=True)
    entity_type = models.CharField(max_length=64, null=True, blank=True)
    entity_id = models.CharField(max_length=64, null=True, blank=True)
    outcome = models.CharField(
        max_length=7,
        choices=Outcome.choices,
        default=Outcome.SUCCESS,
    )
    correlation_id = models.UUIDField(default=uuid4, editable=False, db_index=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    occurred_at = models.DateTimeField(auto_now_add=True, db_index=True)

    objects = AppendOnlyQuerySet.as_manager()

    class Meta:
        ordering = ("-occurred_at", "-id")
        indexes = [
            models.Index(fields=("actor", "occurred_at"), name="audit_actor_time_idx"),
            models.Index(fields=("action", "occurred_at"), name="audit_action_time_idx"),
            models.Index(
                fields=("entity_type", "entity_id", "occurred_at"),
                name="audit_entity_time_idx",
            ),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(
                    action__in=(
                        "LOGIN_SUCCESS", "LOGIN_FAILED", "SESSION_EXPIRED",
                        "USER_CREATED", "USER_DISABLED", "USER_ENABLED",
                        "ROLE_CHANGED", "DONOR_UPDATED", "APPOINTMENT_BOOKED",
                        "APPOINTMENT_CANCELLED", "DONATION_RECORDED",
                        "UNIT_CREATED", "UNIT_RESERVED", "UNIT_RELEASED",
                        "UNIT_ISSUED", "UNIT_EXPIRED", "UNIT_DISCARDED",
                        "UNIT_RETURNED", "REQUEST_SUBMITTED",
                        "REQUEST_APPROVED", "REQUEST_RESERVED", "REQUEST_REJECTED", "REQUEST_HELD",
                        "REQUEST_FULFILLED", "THRESHOLD_CHANGED", "ACCESS_DENIED",
                    )
                ),
                name="audit_action_catalogued",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(entity_type__isnull=True, entity_id__isnull=True)
                    | models.Q(entity_type__isnull=False, entity_id__isnull=False)
                ),
                name="audit_entity_reference_complete",
            ),
        ]

    def save(self, *args, **kwargs):
        if self.pk and type(self).objects.filter(pk=self.pk).exists():
            raise ValidationError("Audit events are append-only.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Audit events are append-only.")
