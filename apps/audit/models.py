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
    action = models.CharField(max_length=64)
    actor_role = models.CharField(max_length=10, null=True, blank=True)
    entity_type = models.CharField(max_length=64, null=True, blank=True)
    entity_id = models.CharField(max_length=64, null=True, blank=True)
    outcome = models.CharField(
        max_length=7,
        choices=Outcome.choices,
        default=Outcome.SUCCESS,
    )
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    occurred_at = models.DateTimeField(auto_now_add=True, db_index=True)

    objects = AppendOnlyQuerySet.as_manager()

    class Meta:
        ordering = ("-occurred_at",)

    def save(self, *args, **kwargs):
        if self.pk and type(self).objects.filter(pk=self.pk).exists():
            raise ValidationError("Audit events are append-only.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Audit events are append-only.")
