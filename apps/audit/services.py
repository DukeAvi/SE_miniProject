"""Audit recording and search operations."""

from .models import AuditEvent


def record_event(*, action: str, actor=None, ip_address=None, entity_type=None,
                 entity_id=None, outcome=AuditEvent.Outcome.SUCCESS) -> AuditEvent:
    """Append a security event without accepting credentials or session data."""
    return AuditEvent.objects.create(
        action=action,
        actor=actor,
        actor_role=getattr(actor, "role", None),
        entity_type=entity_type,
        entity_id=str(entity_id) if entity_id is not None else None,
        outcome=outcome,
        ip_address=ip_address or None,
    )
