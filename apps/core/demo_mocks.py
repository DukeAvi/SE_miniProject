"""In-memory fixtures for Sprint 1 domains that have no persistent models yet."""

from dataclasses import dataclass

from apps.notifications.services import MockNotificationAdapter, NotificationDeliveryError


REQUEST_STATE_SCENARIOS = ("PENDING", "APPROVED", "REJECTED", "ON_HOLD", "FULFILLED")


@dataclass
class MockOutboxEvent:
    event_type: str
    status: str = "PENDING"


class MockNotificationOutbox:
    """Record and deliver synthetic events without a provider or database table."""

    def __init__(self, adapter=None):
        self.adapter = adapter if adapter is not None else MockNotificationAdapter()
        self.events: list[MockOutboxEvent] = []

    def enqueue(self, event_type):
        event = MockOutboxEvent(event_type=event_type)
        self.events.append(event)
        return event

    def deliver_pending(self):
        for event in self.events:
            if event.status != "PENDING":
                continue
            try:
                self.adapter.deliver(event.event_type)
            except NotificationDeliveryError:
                event.status = "FAILED"
            else:
                event.status = "DELIVERED"
