from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient

from apps.audit.models import AuditEvent
from apps.audit.services import record_event
from apps.requests.models import BloodRequest


pytestmark = pytest.mark.django_db

PASSWORD = "Synthetic-Test-Password-532!"


def make_user(role, index=1):
    role_number = {"DONOR": 1, "RECIPIENT": 2, "STAFF": 3, "ADMIN": 4}[role]
    phone_number = role_number * 1000 + index
    return get_user_model().objects.create_user(
        username=f"{role.lower()}-history-{index}@example.test",
        email=f"{role.lower()}-history-{index}@example.test",
        phone=f"+1415555{phone_number:04d}",
        role=role,
        password=PASSWORD,
    )


def make_request(recipient, index=1):
    return BloodRequest.objects.create(
        request_id=f"REQ-HISTORY-{index:04d}",
        requester=recipient,
        patient_name="Synthetic Patient",
        patient_blood_group="A-",
        component="RBC",
        units_needed=2,
        urgency="URGENT",
        hospital="Synthetic General Hospital",
        required_by=timezone.now() + timedelta(days=1),
        contact_phone="+14155550199",
    )


def client_as(user):
    client = APIClient()
    client.force_authenticate(user)
    return client


def test_recipient_lists_only_owned_requests_with_stable_pagination():
    recipient = make_user("RECIPIENT")
    another_recipient = make_user("RECIPIENT", 2)
    older = make_request(recipient, 1)
    newer = make_request(recipient, 2)
    make_request(another_recipient, 3)
    BloodRequest.objects.filter(pk=older.pk).update(
        created_at=timezone.now() - timedelta(days=1)
    )

    response = client_as(recipient).get(
        "/api/v1/requests?page=1&page_size=1"
    )

    assert response.status_code == 200
    assert response.json()["count"] == 2
    assert response.json()["page"] == 1
    assert response.json()["page_size"] == 1
    assert [row["request_id"] for row in response.json()["results"]] == [newer.request_id]
    second_page = client_as(recipient).get(
        "/api/v1/requests?page=2&page_size=1"
    )
    assert [row["request_id"] for row in second_page.json()["results"]] == [older.request_id]


def test_staff_lists_all_requests_but_other_roles_are_denied():
    first = make_user("RECIPIENT")
    second = make_user("RECIPIENT", 2)
    one = make_request(first, 1)
    two = make_request(second, 2)

    response = client_as(make_user("STAFF")).get("/api/v1/requests")
    forbidden = client_as(make_user("ADMIN")).get("/api/v1/requests")

    assert response.status_code == 200
    assert response.json()["count"] == 2
    assert {row["request_id"] for row in response.json()["results"]} == {
        one.request_id,
        two.request_id,
    }
    assert forbidden.status_code == 403


def test_recipient_detail_has_timestamped_status_history_without_private_fields():
    recipient = make_user("RECIPIENT")
    blood_request = make_request(recipient)
    record_event(
        action="REQUEST_SUBMITTED",
        actor=recipient,
        entity_type="BLOOD_REQUEST",
        entity_id=blood_request.pk,
    )
    staff = make_user("STAFF")
    blood_request.status = BloodRequest.Status.APPROVED
    blood_request.reviewer = staff
    blood_request.reviewed_at = timezone.now()
    blood_request.save(update_fields=("status", "reviewer", "reviewed_at"))
    record_event(
        action="REQUEST_APPROVED",
        actor=staff,
        entity_type="BLOOD_REQUEST",
        entity_id=blood_request.pk,
    )

    response = client_as(recipient).get(
        f"/api/v1/requests/{blood_request.request_id}"
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "APPROVED"
    assert body["reviewed_at"]
    assert [item["status"] for item in body["status_history"]] == [
        "PENDING",
        "APPROVED",
    ]
    assert all(item["occurred_at"] for item in body["status_history"])
    assert not {"patient_name", "hospital", "contact_phone"}.intersection(body)


def test_foreign_and_missing_request_details_return_identical_404():
    owner = make_user("RECIPIENT")
    stranger = make_user("RECIPIENT", 2)
    blood_request = make_request(owner)
    client = client_as(stranger)

    foreign = client.get(f"/api/v1/requests/{blood_request.request_id}")
    missing = client.get("/api/v1/requests/REQ-NOT-FOUND")

    assert foreign.status_code == missing.status_code == 404
    assert foreign.json()["error"]["code"] == missing.json()["error"]["code"]
    assert foreign.json()["error"]["message"] == missing.json()["error"]["message"]
    assert foreign.json()["error"]["details"] == missing.json()["error"]["details"]
    assert AuditEvent.objects.filter(
        action="ACCESS_DENIED", actor=stranger, outcome="FAILURE"
    ).count() == 2


def test_donor_cannot_read_request_and_invalid_pagination_is_rejected():
    donor = make_user("DONOR")
    request = make_request(make_user("RECIPIENT"))

    forbidden = client_as(donor).get(f"/api/v1/requests/{request.request_id}")
    invalid = client_as(make_user("RECIPIENT", 2)).get(
        "/api/v1/requests?page=0&page_size=101"
    )

    assert forbidden.status_code == 403
    assert invalid.status_code == 400
    assert invalid.json()["error"]["code"] == "invalid_query"
