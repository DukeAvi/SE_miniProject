from datetime import date, datetime, time, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.audit.models import AuditEvent
from apps.donors.models import Donation, DonorProfile
from apps.inventory.models import BloodUnit


pytestmark = pytest.mark.django_db
TODAY = date(2026, 10, 30)
UNITS_URL = "/api/v1/inventory/units"
AVAILABILITY_URL = "/api/v1/inventory/availability"
BLOOD_GROUPS = ("O-", "O+", "A-", "A+", "B-", "B+", "AB-", "AB+")
COMPONENTS = ("WHOLE_BLOOD", "RBC", "PLASMA", "PLATELETS")


def make_user(role):
    email = f"{role.lower()}-{uuid4().hex[:10]}@example.test"
    return get_user_model().objects.create_user(
        username=email,
        email=email,
        password="Safe-Long-Password-532!",
        role=role,
    )


def make_unit(*, blood_group="O+", component="RBC", status="AVAILABLE", expiry_date=date(2026, 11, 1)):
    donor = make_user("DONOR")
    profile = DonorProfile.objects.create(
        user=donor,
        birth_date=date(1990, 1, 1),
        weight_kg=Decimal("62.00"),
        blood_group=blood_group,
    )
    donation = Donation.objects.create(
        donor=profile,
        donation_date=date(2026, 10, 29),
        blood_group=blood_group,
        component=Donation.Component.WHOLE_BLOOD,
        quantity_units=1,
        status=Donation.Status.COMPLETED,
        screening_weight_kg=Decimal("62.00"),
    )
    return BloodUnit.objects.create(
        donation=donation,
        unit_code=f"BU-{uuid4().hex[:12]}",
        blood_group=blood_group,
        component=component,
        collected_at=datetime.combine(donation.donation_date, time(10), tzinfo=timezone.utc),
        expiry_date=expiry_date,
        quantity_units=1,
        status=status,
    )


def get_client(role):
    client = APIClient()
    client.force_authenticate(make_user(role))
    return client


@pytest.fixture(autouse=True)
def freeze_blood_bank_date(monkeypatch):
    monkeypatch.setattr("apps.inventory.views.blood_bank_today", lambda: TODAY)


@pytest.mark.parametrize("blood_group", BLOOD_GROUPS)
@pytest.mark.parametrize("component", COMPONENTS)
def test_staff_can_search_every_supported_group_and_component(blood_group, component):
    unit = make_unit(blood_group=blood_group, component=component)
    response = get_client("STAFF").get(
        UNITS_URL,
        {"blood_group": blood_group, "component": component},
    )

    assert response.status_code == 200
    assert response.json()["count"] == 1
    assert response.json()["results"][0]["id"] == str(unit.pk)


def test_unit_search_applies_status_and_expiry_filters_independently():
    available = make_unit(expiry_date=date(2026, 10, 31))
    reserved = make_unit(status=BloodUnit.Status.RESERVED, expiry_date=date(2026, 11, 1))
    make_unit(expiry_date=TODAY)
    make_unit(status=BloodUnit.Status.RESERVED, expiry_date=TODAY)
    client = get_client("STAFF")

    available_response = client.get(UNITS_URL, {"status": "AVAILABLE"})
    reserved_response = client.get(UNITS_URL, {"status": "RESERVED"})

    assert [row["id"] for row in available_response.json()["results"]] == [str(available.pk)]
    assert [row["id"] for row in reserved_response.json()["results"]] == [str(reserved.pk)]


def test_unit_search_paginates_with_page_metadata():
    units = [make_unit() for _ in range(3)]

    response = get_client("STAFF").get(UNITS_URL, {"page": 2, "page_size": 2})

    assert response.status_code == 200
    assert response.json()["count"] == 3
    assert response.json()["page"] == 2
    assert response.json()["page_size"] == 2
    assert len(response.json()["results"]) == 1
    assert response.json()["results"][0]["id"] in {str(unit.pk) for unit in units}


@pytest.mark.parametrize(
    ("params", "field"),
    [
        ({"blood_group": "X+"}, "blood_group"),
        ({"component": "SERUM"}, "component"),
        ({"status": "UNKNOWN"}, "status"),
    ],
)
def test_unit_search_rejects_invalid_filters(params, field):
    response = get_client("STAFF").get(UNITS_URL, params)

    assert response.status_code == 400
    assert field in response.json()["error"]["details"]


def test_unit_search_rejects_unknown_query_parameters():
    response = get_client("STAFF").get(UNITS_URL, {"donor_id": str(uuid4())})

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_query"


def test_recipient_gets_aggregate_count_and_nearest_expiry_without_unit_details():
    soon = make_unit(expiry_date=date(2026, 10, 31))
    make_unit(expiry_date=date(2026, 11, 5))
    make_unit(status=BloodUnit.Status.RESERVED, expiry_date=date(2026, 10, 30))
    make_unit(expiry_date=TODAY)

    response = get_client("RECIPIENT").get(
        AVAILABILITY_URL,
        {"blood_group": "O+", "component": "RBC"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "blood_group": "O+",
        "component": "RBC",
        "available_units": 2,
        "nearest_expiry": "2026-10-31",
    }
    assert "unit_code" not in response.json()
    assert soon.status == BloodUnit.Status.AVAILABLE


def test_recipient_empty_aggregate_returns_zero_and_no_nearest_expiry():
    response = get_client("RECIPIENT").get(
        AVAILABILITY_URL,
        {"blood_group": "AB+", "component": "PLATELETS"},
    )

    assert response.status_code == 200
    assert response.json()["available_units"] == 0
    assert response.json()["nearest_expiry"] is None


@pytest.mark.parametrize(
    ("params", "field"),
    [
        ({"component": "RBC"}, "blood_group"),
        ({"blood_group": "X+", "component": "RBC"}, "blood_group"),
        ({"blood_group": "O+"}, "component"),
        ({"blood_group": "O+", "component": "SERUM"}, "component"),
    ],
)
def test_aggregate_rejects_missing_or_invalid_filters(params, field):
    response = get_client("RECIPIENT").get(AVAILABILITY_URL, params)

    assert response.status_code == 400
    assert field in response.json()["error"]["details"]


@pytest.mark.parametrize("role", ["DONOR", "ADMIN"])
def test_donors_and_admins_cannot_search_either_inventory_view(role):
    unit = make_unit()
    client = get_client(role)

    unit_response = client.get(UNITS_URL)
    availability_response = client.get(
        AVAILABILITY_URL,
        {"blood_group": "O+", "component": "RBC"},
    )

    assert unit_response.status_code == 403
    assert availability_response.status_code == 403
    assert AuditEvent.objects.filter(action="ACCESS_DENIED", actor__role=role).count() == 2
    assert unit.status == BloodUnit.Status.AVAILABLE


def test_staff_cannot_use_recipient_aggregate_and_recipient_cannot_view_units():
    unit = make_unit()
    staff = APIClient()
    staff.force_authenticate(make_user("STAFF"))
    recipient = APIClient()
    recipient.force_authenticate(make_user("RECIPIENT"))

    aggregate = staff.get(AVAILABILITY_URL, {"blood_group": "O+", "component": "RBC"})
    unit_search = recipient.get(UNITS_URL)

    assert aggregate.status_code == 403
    assert unit_search.status_code == 403
    assert unit.status == BloodUnit.Status.AVAILABLE
