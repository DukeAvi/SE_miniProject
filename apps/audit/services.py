"""Audit recording and search operations."""

import re
from datetime import UTC, datetime, time, timedelta
from uuid import UUID, uuid4

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from .models import AuditEvent


def record_event(*, action: str, actor=None, ip_address=None, entity_type=None,
                 entity_id=None, outcome=AuditEvent.Outcome.SUCCESS,
                 correlation_id=None) -> AuditEvent:
    """Append a security event without accepting credentials or session data."""
    if action not in AuditEvent.Action.values:
        raise ValidationError("Audit action is not in the approved event catalogue.")
    if outcome not in AuditEvent.Outcome.values:
        raise ValidationError("Audit outcome is invalid.")
    if (entity_type is None) != (entity_id is None):
        raise ValidationError("Audit entity type and identifier must be provided together.")
    if entity_type is not None and not re.fullmatch(r"[A-Z][A-Z0-9_]{0,63}", str(entity_type)):
        raise ValidationError("Audit entity type is invalid.")
    if entity_id is not None and not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", str(entity_id)):
        raise ValidationError("Audit entity identifier is invalid.")
    if correlation_id is not None:
        try:
            correlation_id = UUID(str(correlation_id))
        except (TypeError, ValueError) as exc:
            raise ValidationError("Audit correlation identifier is invalid.") from exc

    return AuditEvent.objects.create(
        action=action,
        actor=actor,
        actor_role=getattr(actor, "role", None),
        entity_type=entity_type,
        entity_id=str(entity_id) if entity_id is not None else None,
        outcome=outcome,
        **({"correlation_id": correlation_id} if correlation_id is not None else {}),
        ip_address=ip_address or None,
    )


def search_events(*, actor_id=None, action=None, from_date=None, to_date=None,
                  entity_type=None, entity_id=None):
    """Return the indexed, newest-first Admin audit query."""
    events = AuditEvent.objects.select_related("actor").all()
    if actor_id is not None:
        events = events.filter(actor_id=actor_id)
    if action is not None:
        events = events.filter(action=action)
    if from_date is not None:
        events = events.filter(
            occurred_at__gte=datetime.combine(from_date, time.min, tzinfo=UTC)
        )
    if to_date is not None:
        events = events.filter(
            occurred_at__lt=datetime.combine(
                to_date + timedelta(days=1),
                time.min,
                tzinfo=UTC,
            )
        )
    if entity_type is not None:
        events = events.filter(entity_type=entity_type, entity_id=entity_id)
    return events.order_by("-occurred_at", "-id")


def _one_year_before(value: datetime) -> datetime:
    """Return the UTC calendar anniversary, clamping leap day to Feb 28."""
    try:
        return value.replace(year=value.year - 1)
    except ValueError:
        return value.replace(year=value.year - 1, day=28)


def run_retention(*, now=None, dry_run=True) -> dict[str, object]:
    """Inspect or purge audit events older than the one-year UTC retention window.

    Deletion is intentionally available only through this service/management
    command path. The public model and queryset deletion APIs remain blocked.
    """
    now = now or timezone.now()
    if timezone.is_naive(now):
        raise ValidationError("Retention time must be timezone-aware.")
    now = now.astimezone(UTC)
    cutoff = _one_year_before(now)
    eligible = AuditEvent.objects.filter(occurred_at__lt=cutoff)
    eligible_count = eligible.count()
    run_id = uuid4()
    audit_fields = {
        "entity_type": "AUDIT_RETENTION_RUN",
        "entity_id": str(run_id),
        "correlation_id": run_id,
    }

    if dry_run:
        record_event(action=AuditEvent.Action.AUDIT_RETENTION_DRY_RUN, **audit_fields)
        return {
            "run_id": run_id,
            "cutoff": cutoff,
            "eligible_count": eligible_count,
            "deleted_count": 0,
            "dry_run": True,
        }

    try:
        with transaction.atomic():
            # _raw_delete bypasses Django's ordinary cascading delete collector;
            # the filter is restricted to the audited, one-year cutoff above.
            deleted_count = eligible._raw_delete(using=eligible.db)
            record_event(action=AuditEvent.Action.AUDIT_RETENTION_RUN, **audit_fields)
    except Exception:
        # The purge transaction rolled back. Preserve a failure trace separately.
        record_event(
            action=AuditEvent.Action.AUDIT_RETENTION_RUN,
            **audit_fields,
            outcome=AuditEvent.Outcome.FAILURE,
        )
        raise

    return {
        "run_id": run_id,
        "cutoff": cutoff,
        "eligible_count": eligible_count,
        "deleted_count": deleted_count,
        "dry_run": False,
    }
