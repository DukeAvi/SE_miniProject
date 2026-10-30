from datetime import date, datetime, time, timezone
from decimal import Decimal
from unittest.mock import patch
from uuid import uuid4

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.audit.models import AuditEvent
from apps.donors.models import Donation, DonorProfile
from apps.inventory.models import BloodUnit


pytestmark = pytest.mark.django_db
URL = "/api/v1/inventory/units"


def user(role, suffix):
    email = f"{role.lower()}{suffix}@example.test"
    return get_user_model().objects.create_user(
        username=email, email=email, password="Safe-Long-Password-532!", role=role,
    )


def completed_donation(suffix=1, *, status=Donation.Status.COMPLETED):
    donor = user("DONOR", suffix)
    profile = DonorProfile.objects.create(
        user=donor,
        birth_date=date(1990, 1, 1),
        weight_kg=Decimal("62.00"),
        blood_group="O+",
    )
    return Donation.objects.create(
        donor=profile,
        donation_date=date(2026, 10, 29),
        blood_group="O+",
        component=Donation.Component.WHOLE_BLOOD,
        quantity_units=1,
        status=status,
        screening_weight_kg=Decimal("62.00"),
    )


def payload(donation, **changes):
    data = {
        "unit_code": "BB-20261029-0001",
        "donation_id": str(donation.pk),
        "blood_group": "O+",
        "component": "RBC",
        "collected_at": datetime.combine(donation.donation_date, time(10), tzinfo=timezone.utc).isoformat(),
        "expiry_date": "2026-11-26",
    }
    data.update(changes)
    return data


def client_as(account):
    client = APIClient()
    client.force_authenticate(account)
    return client


def test_staff_creates_unit_linked_to_completed_donation_with_audit():
    donation = completed_donation()
    staff = user("STAFF", 2)

    response = client_as(staff).post(URL, payload(donation), format="json")

    assert response.status_code == 201
    unit = BloodUnit.objects.get(pk=response.json()["id"])
    assert unit.donation_id == donation.pk
    assert unit.unit_code == "BB-20261029-0001"
    assert unit.status == BloodUnit.Status.AVAILABLE
    assert response.json()["donation_id"] == str(donation.pk)
    assert AuditEvent.objects.filter(action="UNIT_CREATED", actor=staff).count() == 1


def test_unit_code_is_normalized_for_scanner_input_and_unique():
    donation = completed_donation()
    client = client_as(user("STAFF", 3))

    first = client.post(URL, payload(donation, unit_code="bb-20261029-0001"), format="json")
    duplicate = client.post(URL, payload(donation, unit_code="BB-20261029-0001"), format="json")

    assert first.status_code == 201
    assert first.json()["unit_code"] == "BB-20261029-0001"
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "duplicate_unit_code"
    assert BloodUnit.objects.count() == 1
    assert AuditEvent.objects.filter(action="UNIT_CREATED").count() == 1


@pytest.mark.parametrize("role", ["DONOR", "RECIPIENT", "ADMIN"])
def test_only_staff_can_create_units(role):
    donation = completed_donation(4)

    response = client_as(user(role, 5)).post(URL, payload(donation), format="json")

    assert response.status_code == 403
    assert BloodUnit.objects.count() == 0
    assert AuditEvent.objects.filter(action="UNIT_CREATED").count() == 0


def test_missing_donation_is_rejected_without_partial_records():
    staff = user("STAFF", 6)
    data = payload(completed_donation(7))
    data["donation_id"] = str(uuid4())

    response = client_as(staff).post(URL, data, format="json")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "donation_not_found"
    assert BloodUnit.objects.count() == 0
    assert not AuditEvent.objects.filter(action="UNIT_CREATED").exists()


def test_mismatched_donation_details_are_rejected_without_partial_records():
    donation = completed_donation(8)
    staff = user("STAFF", 9)

    response = client_as(staff).post(URL, payload(donation, blood_group="A+"), format="json")

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "blood_group_mismatch"
    assert BloodUnit.objects.count() == 0
    assert not AuditEvent.objects.filter(action="UNIT_CREATED").exists()


@pytest.mark.parametrize("changes", [
    {"unit_code": "unit code with spaces"},
    {"unit_code": ""},
    {"component": "PLASMA'; DROP TABLE apps_inventory_bloodunit; --"},
    {"unexpected": "field"},
])
def test_invalid_input_is_rejected_without_partial_records(changes):
    donation = completed_donation(10)

    response = client_as(user("STAFF", 11)).post(URL, payload(donation, **changes), format="json")

    assert response.status_code == 400
    assert BloodUnit.objects.count() == 0
    assert not AuditEvent.objects.filter(action="UNIT_CREATED").exists()


def test_audit_failure_rolls_back_unit_creation():
    donation = completed_donation(12)
    with patch("apps.inventory.services.record_event", side_effect=RuntimeError("audit unavailable")):
        with pytest.raises(RuntimeError):
            client_as(user("STAFF", 13)).post(URL, payload(donation), format="json")

    assert BloodUnit.objects.count() == 0
    assert not AuditEvent.objects.filter(action="UNIT_CREATED").exists()
