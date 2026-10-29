"""Notification delivery adapters for the demo and automated tests."""

import logging
from typing import Protocol

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


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
    raise ImproperlyConfigured("Unsupported notification provider")
