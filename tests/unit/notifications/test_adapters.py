import pytest
from django.core.exceptions import ImproperlyConfigured

from apps.notifications.services import (
    ConsoleNotificationAdapter,
    MockNotificationAdapter,
    NotificationDeliveryError,
    get_notification_adapter,
)


def test_console_adapter_delivers_without_logging_payload(caplog):
    adapter = ConsoleNotificationAdapter()

    adapter.deliver("request.approved")

    assert "Notification delivered via console adapter" in caplog.text
    assert "request.approved" not in caplog.text


def test_mock_adapter_records_successful_delivery():
    adapter = MockNotificationAdapter()

    adapter.deliver("request.approved")

    assert adapter.delivered_events == ["request.approved"]


def test_mock_adapter_can_simulate_delivery_failure():
    adapter = MockNotificationAdapter(fail=True)

    with pytest.raises(NotificationDeliveryError, match="simulated"):
        adapter.deliver("request.approved")

    assert adapter.delivered_events == []


def test_factory_selects_console_adapter_by_default(settings):
    settings.NOTIFICATION_PROVIDER = "console"

    assert isinstance(get_notification_adapter(), ConsoleNotificationAdapter)


def test_factory_rejects_unconfigured_provider():
    with pytest.raises(ImproperlyConfigured, match="Unsupported notification provider"):
        get_notification_adapter("email")
