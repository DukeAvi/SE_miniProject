from datetime import timedelta
from unittest.mock import patch

import pytest
from django.db import transaction
from django.contrib.auth import get_user_model
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.notifications.models import Notification
from apps.notifications.monitoring import notification_delivery_health
from apps.notifications.services import NotificationDeliveryError
from apps.notifications.tasks import (
    deliver_notification,
    dispatch_queued_notifications,
)
from apps.requests.models import BloodRequest
from apps.requests.services import decide_blood_request


pytestmark = pytest.mark.django_db

PASSWORD = "Synthetic-Test-Password-532!"


def make_user(role, index=1):
    role_number = {"DONOR": 1, "RECIPIENT": 2, "STAFF": 3, "ADMIN": 4}[role]
    phone_number = role_number * 1000 + index
    return get_user_model().objects.create_user(
        username=f"{role.lower()}-notice-{index}@example.test",
        email=f"{role.lower()}-notice-{index}@example.test",
        phone=f"+1415555{phone_number:04d}",
        role=role,
        password=PASSWORD,
    )


def make_request(recipient, index=1):
    return BloodRequest.objects.create(
        request_id=f"REQ-NOTICE-{index:04d}",
        requester=recipient,
        patient_name="Synthetic Patient",
        patient_blood_group="A-",
        component="RBC",
        units_needed=1,
        urgency="URGENT",
        hospital="Synthetic General Hospital",
        required_by=timezone.now() + timedelta(days=1),
        contact_phone="+14155550199",
    )


def make_notification(recipient, index=1, *, status=Notification.Status.QUEUED):
    blood_request = make_request(recipient, index)
    return Notification.objects.create(
        recipient=recipient,
        blood_request=blood_request,
        type=Notification.Type.REQUEST_APPROVED,
        status=status,
        **(
            {"failure_code": "DELIVERY_FAILED", "attempt_count": 5}
            if status == Notification.Status.FAILED
            else {}
        ),
    )


def client_as(user):
    client = APIClient()
    client.force_authenticate(user)
    return client


@pytest.mark.parametrize("role", ["DONOR", "RECIPIENT", "STAFF", "ADMIN"])
def test_users_list_only_their_own_notifications(role):
    owner = make_user(role)
    other = make_user("RECIPIENT", 2)
    own = make_notification(owner, 1)
    make_notification(other, 2)

    response = client_as(owner).get("/api/v1/notifications?page=1&page_size=10")

    assert response.status_code == 200
    assert response.json()["count"] == 1
    assert response.json()["results"][0]["notification_id"] == str(own.pk)
    assert set(response.json()["results"][0]) == {
        "notification_id", "type", "status", "created_at", "low_stock_alert"
    }


def test_notification_list_validates_pagination_and_rejects_unknown_filters():
    user = make_user("RECIPIENT")

    invalid_page = client_as(user).get("/api/v1/notifications?page=0")
    oversized_page = client_as(user).get("/api/v1/notifications?page_size=101")
    unknown_filter = client_as(user).get("/api/v1/notifications?recipient=other")

    assert invalid_page.status_code == 400
    assert invalid_page.json()["error"]["code"] == "invalid_query"
    assert oversized_page.status_code == 400
    assert oversized_page.json()["error"]["code"] == "invalid_query"
    assert unknown_filter.status_code == 400


@pytest.mark.django_db(transaction=True)
def test_outbox_delivery_is_dispatched_only_after_transaction_commit():
    recipient = make_user("RECIPIENT")
    blood_request = make_request(recipient)

    with patch("apps.notifications.tasks.deliver_notification.apply_async") as enqueue:
        with transaction.atomic():
            notification = Notification.objects.create(
                recipient=recipient,
                blood_request=blood_request,
                type=Notification.Type.REQUEST_APPROVED,
            )
            enqueue.assert_not_called()

        enqueue.assert_called_once_with(args=[str(notification.pk)])


def test_admin_can_list_only_sanitized_permanent_delivery_failures():
    admin = make_user("ADMIN")
    owner = make_user("RECIPIENT")
    failed = make_notification(owner, status=Notification.Status.FAILED)
    Notification.objects.filter(pk=failed.pk).update(last_attempt_at=timezone.now())
    queued = make_notification(owner, index=2)

    response = client_as(admin).get("/api/v1/admin/notification-failures")
    forbidden = client_as(make_user("STAFF")).get(
        "/api/v1/admin/notification-failures"
    )

    assert response.status_code == 200
    assert response.json()["count"] == 1
    assert response.json()["results"] == [{
        "notification_id": str(failed.pk),
        "code": "DELIVERY_FAILED",
        "created_at": failed.created_at.isoformat().replace("+00:00", "Z"),
    }]
    assert queued.status == Notification.Status.QUEUED
    assert forbidden.status_code == 403


def test_successful_delivery_is_idempotent_when_task_is_dispatched_twice():
    notification = make_notification(make_user("RECIPIENT"))
    adapter = type("Adapter", (), {"deliver": lambda self, event_type: None})()

    with patch(
        "apps.notifications.services.get_notification_adapter", return_value=adapter
    ) as factory:
        first = deliver_notification.run(str(notification.pk))
        second = deliver_notification.run(str(notification.pk))

    notification.refresh_from_db()
    assert first == {"status": "sent", "attempt_count": 1}
    assert second == {"status": "sent"}
    assert notification.status == Notification.Status.SENT
    assert notification.attempt_count == 1
    assert notification.sent_at is not None
    assert factory.call_count == 1


def test_delivery_retries_with_backoff_then_surfaces_sanitized_failure():
    notification = make_notification(make_user("RECIPIENT"))
    failure = NotificationDeliveryError("contains sensitive provider response")

    with patch(
        "apps.notifications.services.get_notification_adapter",
        side_effect=failure,
    ):
        backoff_seconds = (60, 120, 240, 480)
        for attempt in range(1, 6):
            result = deliver_notification.run(str(notification.pk))
            notification.refresh_from_db()
            assert notification.attempt_count == attempt
            if attempt < 5:
                assert notification.status == Notification.Status.QUEUED
                assert notification.next_attempt_at is not None
                assert (
                    notification.next_attempt_at - notification.last_attempt_at
                ).total_seconds() == backoff_seconds[attempt - 1]
                Notification.objects.filter(pk=notification.pk).update(
                    next_attempt_at=None
                )

    assert result == {"status": "failed", "attempt_count": 5}
    assert notification.status == Notification.Status.FAILED
    assert notification.failure_code == "DELIVERY_FAILED"
    assert "sensitive" not in notification.failure_code
    assert notification.next_attempt_at is None
    assert notification.sent_at is None


def test_provider_failure_does_not_undo_request_decision():
    recipient = make_user("RECIPIENT")
    blood_request = make_request(recipient)
    staff = make_user("STAFF")

    result = decide_blood_request(
        actor=staff,
        request_id=blood_request.request_id,
        decision="APPROVE",
    )

    blood_request.refresh_from_db()
    notification = Notification.objects.get(blood_request=blood_request)
    assert result.status == blood_request.status == "APPROVED"
    assert notification.status == Notification.Status.QUEUED

    with patch(
        "apps.notifications.services.get_notification_adapter",
        side_effect=NotificationDeliveryError("sanitized failure"),
    ):
        deliver_notification.run(str(notification.pk))

    blood_request.refresh_from_db()
    notification.refresh_from_db()
    assert blood_request.status == "APPROVED"
    assert notification.status == Notification.Status.QUEUED
    assert notification.attempt_count == 1


@pytest.mark.django_db(transaction=True)
def test_broker_dispatch_failure_does_not_undo_committed_outbox():
    recipient = make_user("RECIPIENT")
    blood_request = make_request(recipient)
    with patch(
        "apps.notifications.tasks.deliver_notification.apply_async",
        side_effect=RuntimeError("broker is offline"),
    ):
        with transaction.atomic():
            notification = Notification.objects.create(
                recipient=recipient,
                blood_request=blood_request,
                type=Notification.Type.REQUEST_APPROVED,
            )

    assert Notification.objects.filter(pk=notification.pk).exists()


def test_periodic_sweep_dispatches_only_queued_notifications_due_for_retry():
    owner = make_user("RECIPIENT")
    due = make_notification(owner, 1)
    future = make_notification(owner, 2)
    Notification.objects.filter(pk=future.pk).update(
        next_attempt_at=timezone.now() + timedelta(minutes=5)
    )

    with patch("apps.notifications.tasks.deliver_notification.apply_async") as enqueue:
        result = dispatch_queued_notifications.run()

    assert result == {"queued_count": 1}
    enqueue.assert_called_once_with(args=[str(due.pk)])


@override_settings(
    NOTIFICATION_PENDING_ALERT_THRESHOLD=2,
    NOTIFICATION_FAILURE_RATE_ALERT_PERCENT=50,
)
def test_pending_and_failure_rate_monitor_thresholds():
    owner = make_user("RECIPIENT")
    make_notification(owner, 1)
    make_notification(owner, 2)
    failed = make_notification(owner, 3, status=Notification.Status.FAILED)
    Notification.objects.filter(pk=failed.pk).update(last_attempt_at=timezone.now())

    healthy, metrics = notification_delivery_health()

    assert not healthy
    assert metrics["pending_count"] == 2
    assert metrics["pending_threshold"] == 2
    assert metrics["failure_rate_percent_last_hour"] == 100.0
    assert metrics["failure_rate_threshold_percent"] == 50
    assert metrics["alerts"] == [
        "pending_count_threshold_exceeded",
        "failure_rate_threshold_exceeded",
    ]
