from datetime import UTC, datetime
from unittest.mock import patch
from uuid import UUID

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.utils import NotSupportedError
from rest_framework.test import APIClient

from apps.audit.models import AuditEvent
from apps.audit.services import record_event


pytestmark = pytest.mark.django_db

AUDIT_URL = "/api/v1/admin/audit-logs"
PASSWORD = "Synthetic-Test-Password-532!"


def make_user(role, index=1):
    return get_user_model().objects.create_user(
        username=f"{role.lower()}-{index}@example.test",
        email=f"{role.lower()}-{index}@example.test",
        phone=f"+1202555{index:04d}",
        role=role,
        password=PASSWORD,
    )


def test_event_catalogue_contains_every_required_sad_action():
    required = {
        "LOGIN_SUCCESS",
        "LOGIN_FAILED",
        "SESSION_EXPIRED",
        "USER_CREATED",
        "USER_DISABLED",
        "ROLE_CHANGED",
        "DONOR_UPDATED",
        "APPOINTMENT_BOOKED",
        "APPOINTMENT_CANCELLED",
        "DONATION_RECORDED",
        "UNIT_CREATED",
        "UNIT_RESERVED",
        "UNIT_RELEASED",
        "UNIT_ISSUED",
        "UNIT_EXPIRED",
        "UNIT_DISCARDED",
        "UNIT_RETURNED",
        "REQUEST_SUBMITTED",
        "REQUEST_APPROVED",
        "REQUEST_RESERVED",
        "REQUEST_REJECTED",
        "REQUEST_HELD",
        "REQUEST_FULFILLED",
        "THRESHOLD_CHANGED",
        "ACCESS_DENIED",
        "USER_ENABLED",
    }

    assert required == set(AuditEvent.Action.values)


def test_record_helper_captures_protected_metadata_and_utc_time():
    actor = make_user("STAFF")

    event = record_event(
        action="UNIT_ISSUED",
        actor=actor,
        entity_type="BLOOD_UNIT",
        entity_id="00000000-0000-4000-8000-000000000001",
        outcome="SUCCESS",
        ip_address="192.0.2.10",
    )

    assert event.actor == actor
    assert event.actor_role == "STAFF"
    assert event.entity_type == "BLOOD_UNIT"
    assert event.entity_id == "00000000-0000-4000-8000-000000000001"
    assert event.outcome == "SUCCESS"
    assert event.ip_address == "192.0.2.10"
    assert isinstance(event.correlation_id, UUID)
    assert event.occurred_at.utcoffset().total_seconds() == 0


@pytest.mark.parametrize(
    "kwargs",
    [
        {"action": "NOT_CATALOGUED"},
        {"action": "LOGIN_SUCCESS", "outcome": "UNKNOWN"},
        {"action": "LOGIN_SUCCESS", "entity_type": "USER"},
        {
            "action": "LOGIN_SUCCESS",
            "entity_type": "USER",
            "entity_id": "sensitive@example.test",
        },
        {"action": "LOGIN_SUCCESS", "correlation_id": "not-a-uuid"},
    ],
)
def test_record_helper_rejects_uncatalogued_or_unsafe_metadata(kwargs):
    with pytest.raises(ValidationError):
        record_event(**kwargs)

    assert AuditEvent.objects.count() == 0


def test_audit_record_rolls_back_with_business_transaction():
    with pytest.raises(RuntimeError):
        with transaction.atomic():
            record_event(action="REQUEST_APPROVED")
            raise RuntimeError("business operation failed")

    assert AuditEvent.objects.count() == 0


def test_audit_records_are_append_only_through_model_and_queryset_paths():
    event = record_event(action="LOGIN_SUCCESS")

    event.action = "LOGIN_FAILED"
    with pytest.raises(ValidationError):
        event.save()
    with pytest.raises(ValidationError):
        event.delete()
    with pytest.raises(NotSupportedError):
        AuditEvent.objects.filter(pk=event.pk).update(action="LOGIN_FAILED")
    with pytest.raises(NotSupportedError):
        AuditEvent.objects.filter(pk=event.pk).delete()


def test_database_rejects_uncatalogued_actions():
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            AuditEvent.objects.create(action="UNAPPROVED_EVENT")


def test_admin_search_filters_actor_action_dates_and_affected_record():
    admin = make_user("ADMIN")
    staff = make_user("STAFF", 2)
    older = datetime(2026, 10, 20, 9, tzinfo=UTC)
    newer = datetime(2026, 10, 21, 10, tzinfo=UTC)
    with patch("django.utils.timezone.now", return_value=older):
        record_event(
            action="LOGIN_SUCCESS",
            actor=staff,
            entity_type="USER",
            entity_id=staff.pk,
        )
    with patch("django.utils.timezone.now", return_value=newer):
        expected = record_event(
            action="ROLE_CHANGED",
            actor=admin,
            entity_type="USER",
            entity_id=staff.pk,
            ip_address="192.0.2.11",
        )
    client = APIClient()
    client.force_authenticate(admin)

    response = client.get(
        AUDIT_URL,
        {
            "actor": admin.pk,
            "action": "ROLE_CHANGED",
            "from": "2026-10-21",
            "to": "2026-10-21",
            "entity_type": "USER",
            "entity_id": staff.pk,
        },
    )

    assert response.status_code == 200, response.content
    assert response.json()["count"] == 1
    result = response.json()["results"][0]
    assert result["actor_id"] == str(admin.pk)
    assert result["actor_role"] == "ADMIN"
    assert result["action"] == "ROLE_CHANGED"
    assert result["entity_type"] == "USER"
    assert result["entity_id"] == str(staff.pk)
    assert result["outcome"] == "SUCCESS"
    assert result["ip_address"] == "192.0.2.11"
    assert result["correlation_id"] == str(expected.correlation_id)
    assert result["created_at"].startswith("2026-10-21T10:00:00")


def test_admin_search_is_newest_first_and_paginated():
    admin = make_user("ADMIN")
    for index in range(3):
        with patch(
            "django.utils.timezone.now",
            return_value=datetime(2026, 10, 20 + index, 9, tzinfo=UTC),
        ):
            record_event(action="LOGIN_FAILED", actor=admin)
    client = APIClient()
    client.force_authenticate(admin)

    first = client.get(AUDIT_URL, {"page": 1, "page_size": 2})
    second = client.get(AUDIT_URL, {"page": 2, "page_size": 2})

    assert first.status_code == second.status_code == 200
    assert first.json()["count"] == 3
    assert len(first.json()["results"]) == 2
    assert len(second.json()["results"]) == 1
    assert first.json()["results"][0]["created_at"] > first.json()["results"][1]["created_at"]


@pytest.mark.parametrize("role", ["DONOR", "RECIPIENT", "STAFF"])
def test_only_admin_can_read_audit_records(role):
    actor = make_user(role)
    record_event(action="LOGIN_SUCCESS")
    client = APIClient()
    client.force_authenticate(actor)

    response = client.get(AUDIT_URL)

    assert response.status_code == 403


def test_audit_search_requires_authentication():
    assert APIClient().get(AUDIT_URL).status_code == 401


@pytest.mark.parametrize(
    "query",
    [
        {"unexpected": "value"},
        {"actor": "not-an-id"},
        {"action": "NOT_CATALOGUED"},
        {"from": "2026-10-22", "to": "2026-10-21"},
        {"entity_type": "USER"},
        {"entity_id": "1"},
        {"entity_type": "user", "entity_id": "1"},
        {"page": 0},
        {"page_size": 101},
    ],
)
def test_invalid_search_filters_are_rejected(query):
    admin = make_user("ADMIN")
    client = APIClient()
    client.force_authenticate(admin)

    response = client.get(AUDIT_URL, query)

    assert response.status_code == 400
