from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient

from apps.audit.models import AuditEvent
from apps.notifications.models import Notification
from apps.requests.models import BloodRequest
from apps.requests.services import BloodRequestRejected, decide_blood_request


pytestmark = pytest.mark.django_db

PASSWORD = "Synthetic-Test-Password-532!"


def make_user(role, index=1, *, is_active=True):
    return get_user_model().objects.create_user(
        username=f"{role.lower()}-decision-{index}@example.test",
        email=f"{role.lower()}-decision-{index}@example.test",
        phone=f"+1310555{index:04d}",
        role=role,
        is_active=is_active,
        password=PASSWORD,
    )


def make_request(recipient=None, index=1):
    recipient = recipient or make_user("RECIPIENT", index)
    return BloodRequest.objects.create(
        request_id=f"REQ-TEST-{index:04d}",
        requester=recipient,
        patient_name="Synthetic Patient",
        patient_blood_group="A-",
        component="RBC",
        units_needed=2,
        urgency="URGENT",
        hospital="Synthetic General Hospital",
        required_by=timezone.now() + timedelta(days=1),
        contact_phone="+13105550199",
    )


def client_as(user):
    client = APIClient()
    client.force_authenticate(user)
    return client


def decision_url(blood_request):
    return f"/api/v1/requests/{blood_request.request_id}/decision"


@pytest.mark.parametrize(
    ("decision", "reason", "expected_status", "audit_action", "notification_type"),
    [
        ("APPROVE", None, "APPROVED", "REQUEST_APPROVED", "REQUEST_APPROVED"),
        ("REJECT", "Clinical details require correction", "REJECTED", "REQUEST_REJECTED", "REQUEST_REJECTED"),
        ("HOLD", "Awaiting verification", "ON_HOLD", "REQUEST_HELD", "REQUEST_HELD"),
    ],
)
def test_staff_decision_updates_request_audit_and_outbox_together(
    decision, reason, expected_status, audit_action, notification_type
):
    blood_request = make_request()
    staff = make_user("STAFF", 2)
    payload = {"decision": decision}
    if reason is not None:
        payload["reason"] = reason

    response = client_as(staff).post(
        decision_url(blood_request), payload, format="json"
    )

    assert response.status_code == 200, response.content
    assert response.json()["status"] == expected_status
    blood_request.refresh_from_db()
    assert blood_request.status == expected_status
    assert blood_request.reviewer == staff
    assert blood_request.reviewed_at is not None
    assert blood_request.decision_reason == (reason or "")
    event = AuditEvent.objects.get(action=audit_action)
    assert event.actor == staff
    assert event.actor_role == "STAFF"
    assert event.entity_type == "BLOOD_REQUEST"
    assert event.entity_id == str(blood_request.pk)
    notice = Notification.objects.get()
    assert notice.recipient == blood_request.requester
    assert notice.blood_request == blood_request
    assert notice.type == notification_type
    assert notice.status == "QUEUED"


@pytest.mark.parametrize("decision", ["REJECT", "HOLD"])
@pytest.mark.parametrize("reason", [None, "", "   "])
def test_reject_and_hold_require_a_nonempty_reason(decision, reason):
    blood_request = make_request()
    staff = make_user("STAFF", 2)
    payload = {"decision": decision}
    if reason is not None:
        payload["reason"] = reason

    response = client_as(staff).post(
        decision_url(blood_request), payload, format="json"
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "reason_required"
    assert "reason" in response.json()["error"]["details"]
    blood_request.refresh_from_db()
    assert blood_request.status == "PENDING"
    assert blood_request.reviewer is None
    assert not AuditEvent.objects.filter(action__startswith="REQUEST_").exists()
    assert Notification.objects.count() == 0


def test_approval_accepts_optional_reason_at_the_documented_boundary():
    blood_request = make_request()
    staff = make_user("STAFF", 2)
    reason = "R" * 500

    response = client_as(staff).post(
        decision_url(blood_request),
        {"decision": "APPROVE", "reason": reason},
        format="json",
    )

    assert response.status_code == 200
    blood_request.refresh_from_db()
    assert blood_request.decision_reason == reason


@pytest.mark.parametrize("role", ["DONOR", "RECIPIENT", "ADMIN"])
def test_non_staff_roles_cannot_decide_requests(role):
    blood_request = make_request()
    actor = make_user(role, 2)

    response = client_as(actor).post(
        decision_url(blood_request), {"decision": "APPROVE"}, format="json"
    )

    assert response.status_code == 403
    blood_request.refresh_from_db()
    assert blood_request.status == "PENDING"
    assert not AuditEvent.objects.filter(action="REQUEST_APPROVED").exists()
    assert Notification.objects.count() == 0


def test_decision_requires_authentication():
    blood_request = make_request()

    response = APIClient().post(
        decision_url(blood_request), {"decision": "APPROVE"}, format="json"
    )

    assert response.status_code == 401
    blood_request.refresh_from_db()
    assert blood_request.status == "PENDING"


def test_service_rechecks_staff_role_and_active_state():
    blood_request = make_request()
    inactive_staff = make_user("STAFF", 2, is_active=False)

    with pytest.raises(BloodRequestRejected) as rejected:
        decide_blood_request(
            actor=inactive_staff,
            request_id=blood_request.request_id,
            decision="APPROVE",
        )

    assert rejected.value.code == "forbidden"
    blood_request.refresh_from_db()
    assert blood_request.status == "PENDING"


def test_repeated_decision_returns_conflict_without_new_side_effects():
    blood_request = make_request()
    staff = make_user("STAFF", 2)
    client = client_as(staff)
    first = client.post(
        decision_url(blood_request), {"decision": "APPROVE"}, format="json"
    )

    repeated = client.post(
        decision_url(blood_request),
        {"decision": "REJECT", "reason": "Changed decision"},
        format="json",
    )

    assert first.status_code == 200
    assert repeated.status_code == 409
    assert repeated.json()["error"]["code"] == "invalid_state_transition"
    blood_request.refresh_from_db()
    assert blood_request.status == "APPROVED"
    assert blood_request.decision_reason == ""
    assert AuditEvent.objects.filter(action__startswith="REQUEST_").count() == 1
    assert Notification.objects.count() == 1


@pytest.mark.parametrize(
    "source_status",
    ["APPROVED", "REJECTED", "ON_HOLD", "RESERVED", "FULFILLED"],
)
@pytest.mark.parametrize("decision", ["APPROVE", "REJECT", "HOLD"])
def test_every_nonpending_source_state_rejects_every_review_decision(
    source_status, decision
):
    blood_request = make_request()
    prior_reviewer = make_user("STAFF", 2)
    actor = make_user("STAFF", 3)
    BloodRequest.objects.filter(pk=blood_request.pk).update(
        status=source_status,
        reviewer=prior_reviewer,
        reviewed_at=timezone.now(),
        decision_reason=(
            "Existing decision" if source_status in ("REJECTED", "ON_HOLD") else ""
        ),
    )

    response = client_as(actor).post(
        decision_url(blood_request),
        {
            "decision": decision,
            **(
                {"reason": "New decision"}
                if decision in ("REJECT", "HOLD")
                else {}
            ),
        },
        format="json",
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "invalid_state_transition"
    blood_request.refresh_from_db()
    assert blood_request.status == source_status
    assert blood_request.reviewer == prior_reviewer
    assert not AuditEvent.objects.filter(action__startswith="REQUEST_").exists()
    assert Notification.objects.count() == 0


@pytest.mark.parametrize(
    ("payload", "field"),
    [
        ({}, "decision"),
        ({"decision": "DEFER"}, "decision"),
        ({"decision": True}, "decision"),
        ({"decision": "APPROVE", "reason": ["not", "text"]}, "reason"),
        ({"decision": "APPROVE", "reason": "R" * 501}, "reason"),
        ({"decision": "APPROVE", "unexpected": True}, "non_field_errors"),
    ],
)
def test_invalid_decision_input_changes_nothing(payload, field):
    blood_request = make_request()
    staff = make_user("STAFF", 2)

    response = client_as(staff).post(
        decision_url(blood_request), payload, format="json"
    )

    assert response.status_code == 400
    assert field in response.json()["error"]["details"]
    blood_request.refresh_from_db()
    assert blood_request.status == "PENDING"
    assert Notification.objects.count() == 0


def test_query_parameters_are_rejected_without_a_decision():
    blood_request = make_request()
    staff = make_user("STAFF", 2)

    response = client_as(staff).post(
        f"{decision_url(blood_request)}?source=external",
        {"decision": "APPROVE"},
        format="json",
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_query"
    blood_request.refresh_from_db()
    assert blood_request.status == "PENDING"


def test_missing_request_returns_not_found_without_side_effects():
    staff = make_user("STAFF", 2)

    response = client_as(staff).post(
        "/api/v1/requests/REQ-MISSING/decision",
        {"decision": "APPROVE"},
        format="json",
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "request_not_found"
    assert Notification.objects.count() == 0
    assert not AuditEvent.objects.filter(action="REQUEST_APPROVED").exists()


def test_audit_failure_rolls_back_request_and_outbox(monkeypatch):
    blood_request = make_request()
    staff = make_user("STAFF", 2)

    def fail_audit(**kwargs):
        raise RuntimeError("audit unavailable")

    monkeypatch.setattr("apps.requests.services.record_event", fail_audit)
    with pytest.raises(RuntimeError, match="audit unavailable"):
        decide_blood_request(
            actor=staff,
            request_id=blood_request.request_id,
            decision="APPROVE",
        )

    blood_request.refresh_from_db()
    assert blood_request.status == "PENDING"
    assert blood_request.reviewer is None
    assert Notification.objects.count() == 0


def test_outbox_failure_rolls_back_request_and_audit(monkeypatch):
    blood_request = make_request()
    staff = make_user("STAFF", 2)

    def fail_outbox(**kwargs):
        raise RuntimeError("outbox unavailable")

    monkeypatch.setattr("apps.requests.services.Notification.objects.create", fail_outbox)
    with pytest.raises(RuntimeError, match="outbox unavailable"):
        decide_blood_request(
            actor=staff,
            request_id=blood_request.request_id,
            decision="APPROVE",
        )

    blood_request.refresh_from_db()
    assert blood_request.status == "PENDING"
    assert blood_request.reviewer is None
    assert not AuditEvent.objects.filter(action="REQUEST_APPROVED").exists()


def test_decision_requires_csrf_for_session_authentication():
    blood_request = make_request()
    staff = make_user("STAFF", 2)
    client = APIClient(enforce_csrf_checks=True)
    csrf_token = client.get("/api/v1/auth/csrf", secure=True).json()["csrfToken"]
    login = client.post(
        "/api/v1/auth/login",
        {"email": staff.email, "password": PASSWORD},
        format="json",
        secure=True,
        HTTP_REFERER="https://testserver/",
        HTTP_X_CSRFTOKEN=csrf_token,
    )
    assert login.status_code == 200
    csrf_token = client.get("/api/v1/auth/csrf", secure=True).json()["csrfToken"]

    rejected = client.post(
        decision_url(blood_request),
        {"decision": "APPROVE"},
        format="json",
        secure=True,
        HTTP_REFERER="https://testserver/",
    )
    accepted = client.post(
        decision_url(blood_request),
        {"decision": "APPROVE"},
        format="json",
        secure=True,
        HTTP_REFERER="https://testserver/",
        HTTP_X_CSRFTOKEN=csrf_token,
    )

    assert rejected.status_code == 403
    assert rejected.json()["error"]["code"] == "csrf_failed"
    assert accepted.status_code == 200
