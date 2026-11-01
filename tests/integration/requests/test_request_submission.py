from datetime import timedelta
import re
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient

from apps.audit.models import AuditEvent
from apps.requests.models import BloodRequest
from apps.requests.services import BloodRequestRejected, submit_blood_request


pytestmark = pytest.mark.django_db

REQUEST_URL = "/api/v1/requests"
PASSWORD = "Synthetic-Test-Password-532!"


def make_user(role, index=1, *, is_active=True):
    return get_user_model().objects.create_user(
        username=f"{role.lower()}-{index}@example.test",
        email=f"{role.lower()}-{index}@example.test",
        phone=f"+1202555{index:04d}",
        role=role,
        is_active=is_active,
        password=PASSWORD,
    )


def payload(**overrides):
    data = {
        "patient_name": "Synthetic Patient",
        "patient_blood_group": "A-",
        "component": "RBC",
        "units_needed": 2,
        "urgency": "URGENT",
        "hospital": "Synthetic General Hospital",
        "required_by": (timezone.now() + timedelta(days=1)).isoformat(),
        "contact_phone": "+1 202 555 0199",
    }
    data.update(overrides)
    return data


def test_recipient_submits_pending_request_with_private_response_and_audit_event():
    recipient = make_user("RECIPIENT")
    client = APIClient()
    client.force_authenticate(recipient)

    response = client.post(REQUEST_URL, payload(), format="json")

    assert response.status_code == 201, response.content
    assert set(response.json()) == {
        "request_id",
        "patient_blood_group",
        "component",
        "units_needed",
        "urgency",
        "status",
        "created_at",
    }
    assert re.fullmatch(
        rf"REQ-{timezone.now().year}-[0-9A-F]{{16}}",
        response.json()["request_id"],
    )
    assert response.json()["status"] == "PENDING"
    record = BloodRequest.objects.get(request_id=response.json()["request_id"])
    assert record.requester == recipient
    assert record.patient_name == "Synthetic Patient"
    assert record.hospital == "Synthetic General Hospital"
    assert record.contact_phone == "+12025550199"
    assert AuditEvent.objects.filter(
        action="REQUEST_SUBMITTED",
        actor=recipient,
        ip_address="127.0.0.1",
    ).count() == 1


def test_request_numbers_are_unique_and_human_readable():
    recipient = make_user("RECIPIENT")
    client = APIClient()
    client.force_authenticate(recipient)

    first = client.post(REQUEST_URL, payload(), format="json")
    second = client.post(REQUEST_URL, payload(), format="json")

    assert first.status_code == second.status_code == 201
    assert first.json()["request_id"] != second.json()["request_id"]
    assert BloodRequest.objects.count() == 2


@pytest.mark.parametrize("role", ["DONOR", "STAFF", "ADMIN"])
def test_non_recipient_roles_cannot_submit_requests(role):
    actor = make_user(role)
    client = APIClient()
    client.force_authenticate(actor)

    response = client.post(REQUEST_URL, payload(), format="json")

    assert response.status_code == 403
    assert BloodRequest.objects.count() == 0
    assert not AuditEvent.objects.filter(action="REQUEST_SUBMITTED").exists()


def test_request_submission_requires_authentication():
    response = APIClient().post(REQUEST_URL, payload(), format="json")

    assert response.status_code == 401
    assert BloodRequest.objects.count() == 0


def test_request_submission_requires_csrf_for_session_authentication():
    recipient = make_user("RECIPIENT")
    client = APIClient(enforce_csrf_checks=True)
    csrf_token = client.get("/api/v1/auth/csrf", secure=True).json()["csrfToken"]
    login = client.post(
        "/api/v1/auth/login",
        {"email": recipient.email, "password": PASSWORD},
        format="json",
        secure=True,
        HTTP_REFERER="https://testserver/",
        HTTP_X_CSRFTOKEN=csrf_token,
    )
    assert login.status_code == 200
    csrf_token = client.get("/api/v1/auth/csrf", secure=True).json()["csrfToken"]

    rejected = client.post(
        REQUEST_URL,
        payload(),
        format="json",
        secure=True,
        HTTP_REFERER="https://testserver/",
    )
    accepted = client.post(
        REQUEST_URL,
        payload(),
        format="json",
        secure=True,
        HTTP_REFERER="https://testserver/",
        HTTP_X_CSRFTOKEN=csrf_token,
    )

    assert rejected.status_code == 403
    assert rejected.json()["error"]["code"] == "csrf_failed"
    assert accepted.status_code == 201
    assert BloodRequest.objects.count() == 1


@pytest.mark.parametrize(
    ("overrides", "field"),
    [
        ({"patient_name": ""}, "patient_name"),
        ({"patient_blood_group": "X+"}, "patient_blood_group"),
        ({"component": "UNKNOWN"}, "component"),
        ({"units_needed": 0}, "units_needed"),
        ({"urgency": "IMMEDIATE"}, "urgency"),
        ({"hospital": ""}, "hospital"),
        ({"required_by": (timezone.now() - timedelta(seconds=1)).isoformat()}, "required_by"),
        ({"required_by": "not-a-date"}, "required_by"),
        ({"contact_phone": "123"}, "contact_phone"),
    ],
)
def test_invalid_fields_save_nothing(overrides, field):
    recipient = make_user("RECIPIENT")
    client = APIClient()
    client.force_authenticate(recipient)

    response = client.post(REQUEST_URL, payload(**overrides), format="json")

    assert response.status_code == 400
    assert field in response.json()["error"]["details"]
    assert BloodRequest.objects.count() == 0
    assert not AuditEvent.objects.filter(action="REQUEST_SUBMITTED").exists()


@pytest.mark.parametrize(
    ("overrides", "field"),
    [
        ({"patient_name": ["not", "text"]}, "patient_name"),
        ({"units_needed": True}, "units_needed"),
        ({"required_by": 12345}, "required_by"),
    ],
)
def test_invalid_json_types_save_nothing(overrides, field):
    recipient = make_user("RECIPIENT")
    client = APIClient()
    client.force_authenticate(recipient)

    response = client.post(REQUEST_URL, payload(**overrides), format="json")

    assert response.status_code == 400
    assert field in response.json()["error"]["details"]
    assert BloodRequest.objects.count() == 0


@pytest.mark.parametrize(
    "missing",
    [
        "patient_name",
        "patient_blood_group",
        "component",
        "units_needed",
        "urgency",
        "hospital",
        "required_by",
        "contact_phone",
    ],
)
def test_each_missing_required_field_saves_nothing(missing):
    recipient = make_user("RECIPIENT")
    client = APIClient()
    client.force_authenticate(recipient)
    data = payload()
    data.pop(missing)

    response = client.post(REQUEST_URL, data, format="json")

    assert response.status_code == 400
    assert missing in response.json()["error"]["details"]
    assert BloodRequest.objects.count() == 0


def test_unknown_fields_save_nothing():
    recipient = make_user("RECIPIENT")
    client = APIClient()
    client.force_authenticate(recipient)

    response = client.post(
        REQUEST_URL,
        payload(unexpected="value"),
        format="json",
    )

    assert response.status_code == 400
    assert "non_field_errors" in response.json()["error"]["details"]
    assert BloodRequest.objects.count() == 0


def test_query_parameters_are_rejected_without_creating_request():
    recipient = make_user("RECIPIENT")
    client = APIClient()
    client.force_authenticate(recipient)

    response = client.post(f"{REQUEST_URL}?source=external", payload(), format="json")

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_query"
    assert BloodRequest.objects.count() == 0


def test_service_rechecks_role_and_active_state():
    actor = make_user("RECIPIENT", is_active=False)

    with pytest.raises(BloodRequestRejected) as rejected:
        submit_blood_request(
            actor=actor,
            **payload(required_by=timezone.now() + timedelta(days=1)),
        )

    assert rejected.value.code == "forbidden"
    assert BloodRequest.objects.count() == 0


def test_audit_failure_rolls_back_request_creation():
    recipient = make_user("RECIPIENT")

    with patch("apps.requests.services.record_event", side_effect=RuntimeError("audit unavailable")):
        with pytest.raises(RuntimeError):
            submit_blood_request(
                actor=recipient,
                **payload(required_by=timezone.now() + timedelta(days=1)),
            )

    assert BloodRequest.objects.count() == 0
