"""Audit recording and search operations."""

from .models import AuditEvent


def record_event(*, action: str, actor=None, ip_address=None) -> AuditEvent:
    """Append a security event without accepting credentials or session data."""
    return AuditEvent.objects.create(
        action=action,
        actor=actor,
        ip_address=ip_address or None,
    )
