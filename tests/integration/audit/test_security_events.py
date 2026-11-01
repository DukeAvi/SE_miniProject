import logging
from datetime import timedelta

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import RequestFactory, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.middleware import SessionExpiryMiddleware
from apps.accounts.models import FailedLoginAlertWindow
from apps.accounts.services import record_login_event, track_failed_login_alert
from apps.audit.models import AuditEvent
from apps.audit.services import record_event


pytestmark = pytest.mark.django_db

CSRF_URL = "/api/v1/auth/csrf"
LOGIN_URL = "/api/v1/auth/login"


def make_user(role="STAFF"):
    return get_user_model().objects.create_user(
        username=f"security-{role.lower()}@example.test",
        email=f"security-{role.lower()}@example.test",
        phone="+12025550123",
        role=role,
        password="Synthetic-Test-Password-532!",
    )


def test_failed_login_alert_defaults_match_the_security_requirement():
    assert settings.FAILED_LOGIN_ALERT_THRESHOLD == 20
    assert settings.FAILED_LOGIN_ALERT_WINDOW_SECONDS == 60


@pytest.mark.parametrize("action", AuditEvent.Action.values)
def test_every_catalogued_security_event_accepts_only_protected_metadata(action):
    actor = make_user()

    event = record_event(
        action=action,
        actor=actor,
        entity_type="TEST_RECORD",
        entity_id="synthetic-001",
        outcome="SUCCESS",
        ip_address="192.0.2.10",
    )

    assert event.actor == actor
    assert event.actor_role == "STAFF"
    assert event.action == action
    assert event.entity_type == "TEST_RECORD"
    assert event.entity_id == "synthetic-001"
    assert event.outcome == "SUCCESS"
    assert event.ip_address == "192.0.2.10"
    assert event.correlation_id is not None
    assert event.occurred_at is not None
    assert not hasattr(event, "password")
    assert not hasattr(event, "token")
    assert not hasattr(event, "session_value")
    assert not hasattr(event, "details")


def test_failed_authentication_and_session_expiry_use_failure_outcome():
    actor = make_user()
    record_login_event(
        action="LOGIN_FAILED",
        actor=actor,
        ip_address="192.0.2.20",
    )
    request = RequestFactory().get("/api/v1/users/me", REMOTE_ADDR="192.0.2.21")
    SessionExpiryMiddleware._record_expiry(request, actor)

    login_event = AuditEvent.objects.get(action="LOGIN_FAILED")
    expiry_event = AuditEvent.objects.get(action="SESSION_EXPIRED")
    assert login_event.outcome == expiry_event.outcome == "FAILURE"
    assert login_event.actor_role == expiry_event.actor_role == "STAFF"
    assert login_event.ip_address == "192.0.2.20"
    assert expiry_event.ip_address == "192.0.2.21"


@override_settings(
    FAILED_LOGIN_ALERT_THRESHOLD=20,
    FAILED_LOGIN_ALERT_WINDOW_SECONDS=60,
)
def test_more_than_twenty_failures_emit_one_sanitized_alert(caplog):
    source = "192.0.2.30"
    caplog.set_level(logging.WARNING, logger="apps.security.alerts")

    results = [track_failed_login_alert(ip_address=source) for _ in range(22)]

    assert results[:20] == [False] * 20
    assert results[20] is True
    assert results[21] is False
    window = FailedLoginAlertWindow.objects.get()
    assert window.failed_attempts == 22
    assert window.alerted_at is not None
    assert source not in window.address_key_hash
    alerts = [
        record
        for record in caplog.records
        if record.name == "apps.security.alerts"
        and record.getMessage() == "Failed-login rate threshold exceeded"
    ]
    assert len(alerts) == 1
    assert alerts[0].failed_attempts == 21
    assert alerts[0].window_seconds == 60
    assert source not in caplog.text


@override_settings(
    FAILED_LOGIN_ALERT_THRESHOLD=1,
    FAILED_LOGIN_ALERT_WINDOW_SECONDS=60,
)
def test_failed_login_alert_window_resets_at_the_boundary():
    started_at = timezone.now()

    assert not track_failed_login_alert(ip_address="192.0.2.40", now=started_at)
    assert track_failed_login_alert(ip_address="192.0.2.40", now=started_at)
    next_window = started_at + timedelta(seconds=60)
    assert not track_failed_login_alert(ip_address="192.0.2.40", now=next_window)

    window = FailedLoginAlertWindow.objects.get()
    assert window.failed_attempts == 1
    assert window.window_started_at == next_window
    assert window.alerted_at is None


@override_settings(
    LOGIN_THROTTLE_ATTEMPTS=1,
    LOGIN_THROTTLE_WINDOW_SECONDS=60,
    FAILED_LOGIN_ALERT_THRESHOLD=2,
    FAILED_LOGIN_ALERT_WINDOW_SECONDS=60,
    PASSWORD_HASHERS=("django.contrib.auth.hashers.MD5PasswordHasher",),
)
def test_throttled_failures_still_contribute_to_the_rate_alert(caplog):
    client = APIClient(enforce_csrf_checks=True)
    token = client.get(CSRF_URL, secure=True).json()["csrfToken"]
    caplog.set_level(logging.WARNING, logger="apps.security.alerts")

    responses = [
        client.post(
            LOGIN_URL,
            {"email": "unknown@example.test", "password": "wrong-password"},
            format="json",
            secure=True,
            REMOTE_ADDR="192.0.2.50",
            HTTP_REFERER="https://testserver/",
            HTTP_X_CSRFTOKEN=token,
        )
        for _ in range(3)
    ]

    assert [response.status_code for response in responses] == [401, 429, 429]
    assert FailedLoginAlertWindow.objects.get().failed_attempts == 3
    assert len(
        [record for record in caplog.records if record.name == "apps.security.alerts"]
    ) == 1
    events = AuditEvent.objects.filter(action="LOGIN_FAILED").order_by("id")
    assert events.count() == 3
    assert all(event.outcome == "FAILURE" for event in events)
    assert all(event.ip_address == "192.0.2.50" for event in events)
    assert "unknown@example.test" not in caplog.text
    assert "wrong-password" not in caplog.text
