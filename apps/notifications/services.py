"""Notification delivery adapters for the demo and automated tests."""

import logging
from typing import Protocol

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from .models import Notification


logger = logging.getLogger(__name__)


class NotificationDeliveryError(RuntimeError):
    """Raised when a notification adapter cannot deliver an event."""


class NotificationAdapter(Protocol):
    def deliver(self, event_type: str) -> None:
        """Deliver an event without requiring callers to know the provider."""


class ConsoleNotificationAdapter:
    """A local demo adapter that logs no recipient or message content."""

    def deliver(self, event_type: str) -> None:
        if not event_type:
            raise ValueError("event_type is required")
        logger.info("Notification delivered via console adapter")


class MockNotificationAdapter:
    """Deterministic adapter for tests, including simulated provider failures."""

    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.delivered_events: list[str] = []

    def deliver(self, event_type: str) -> None:
        if not event_type:
            raise ValueError("event_type is required")
        if self.fail:
            raise NotificationDeliveryError("simulated notification delivery failure")
        self.delivered_events.append(event_type)


def get_notification_adapter(provider: str | None = None) -> NotificationAdapter:
    """Return the configured delivery adapter; unsupported providers fail closed."""
    selected_provider = (
        provider if provider is not None else settings.NOTIFICATION_PROVIDER
    )
    if selected_provider == "console":
        return ConsoleNotificationAdapter()
    if selected_provider == "mock":
        return MockNotificationAdapter()
    raise ImproperlyConfigured("Unsupported notification provider")


MAX_DELIVERY_ATTEMPTS = 5
RETRY_BACKOFF_SECONDS = (60, 120, 240, 480)


def dispatch_notification(notification_id: str) -> None:
    """Schedule delivery after the outbox transaction commits."""
    from .tasks import deliver_notification

    transaction.on_commit(
        lambda: _safe_enqueue(deliver_notification, str(notification_id)),
        robust=True,
    )


def _safe_enqueue(task, notification_id: str) -> None:
    try:
        task.apply_async(args=[notification_id])
    except Exception:
        logger.warning(
            "Notification dispatch could not reach the worker; the outbox sweep will retry"
        )


def due_notification_ids(*, now=None, limit=500):
    """Return queued notification IDs that are ready for asynchronous delivery."""
    now = now or timezone.now()
    return list(
        Notification.objects.filter(status=Notification.Status.QUEUED)
        .filter(Q(next_attempt_at__isnull=True) | Q(next_attempt_at__lte=now))
        .order_by("created_at", "id")
        .values_list("id", flat=True)[:limit]
    )
