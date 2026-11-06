import csv
from datetime import date, datetime, timedelta
from io import StringIO
from unittest.mock import patch
from zoneinfo import ZoneInfo

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import AccountRole
from apps.donors.models import Donation, DonorProfile
from apps.inventory.models import BloodUnit, InventoryTransaction
from apps.requests.models import BloodAllocation, BloodRequest


pytestmark = pytest.mark.django_db

REPORT_URL = "/api/v1/reports/{}"
PASSWORD = "Safe-Long-Password-532!"
REPORT_DATE = date(2026, 11, 4)
REPORT_QUERY = f"?from={REPORT_DATE.isoformat()}&to={REPORT_DATE.isoformat()}"
LOCAL_ZONE = ZoneInfo("Asia/Kolkata")


def make_user(role, index):
    email = f"{role.lower()}{index}@reports.example.test"
    role_number = {
        AccountRole.DONOR: 1,
        AccountRole.RECIPIENT: 2,
        AccountRole.STAFF: 3,
        AccountRole.ADMIN: 4,
    }[role]
    return get_user_model().objects.create_user(
        username=f"report-user-{role.lower()}-{index}",
        email=email,
        password=PASSWORD,
        first_name="Report",
        last_name="User",
        phone=f"+1202{role_number}{index:06d}",
        role=role,
    )


@pytest.fixture
def staff_client():
    client = APIClient()
    client.force_authenticate(make_user(AccountRole.STAFF, 1))
    return client


def make_donation(index, *, donation_date=REPORT_DATE, component=Donation.Component.RBC,
                  blood_group="A+", quantity_units=1):
    donor = make_user(AccountRole.DONOR, index)
    profile = DonorProfile.objects.create(
        user=donor,
        birth_date=date(1990, 1, 1),
        weight_kg="65.00",
        blood_group=blood_group,
    )
    return Donation.objects.create(
        donor=profile,
        donation_date=donation_date,
        blood_group=blood_group,
        component=component,
        quantity_units=quantity_units,
        screening_weight_kg="65.00",
    )


def make_unit(donation, index, *, collected_at=None, quantity_units=1):
    collected_at = collected_at or datetime(2026, 11, 4, 4, 0, tzinfo=LOCAL_ZONE)
    return BloodUnit.objects.create(
        donation=donation,
        unit_code=f"REPORT-{index:04d}",
        blood_group=donation.blood_group,
        component=donation.component,
        collected_at=collected_at,
        expiry_date=collected_at.date() + timedelta(days=35),
        quantity_units=quantity_units,
    )


def make_request(index, *, created_at=None, status=BloodRequest.Status.PENDING):
    actor = make_user(AccountRole.RECIPIENT, index)
    request = BloodRequest.objects.create(
        request_id=f"REQ-2026-{index:016X}",
        requester=actor,
        patient_name=f"Private Patient {index}",
        patient_blood_group="A+",
        component="RBC",
        units_needed=2,
        urgency="URGENT",
        hospital=f"Private Hospital {index}",
        required_by=timezone.now() + timedelta(days=1),
        contact_phone=f"+1202555{index:04d}",
        status=status,
    )
    report_created_at = created_at or datetime(2026, 11, 4, 10, 0, tzinfo=LOCAL_ZONE)
    BloodRequest.objects.filter(pk=request.pk).update(created_at=report_created_at)
    request.refresh_from_db()
    return request


@pytest.mark.parametrize("role", [AccountRole.STAFF, AccountRole.ADMIN])
@pytest.mark.parametrize("resource", ["donations", "inventory", "requests", "issued-units"])
def test_staff_and_admin_can_read_each_operational_report(role, resource):
    client = APIClient()
    client.force_authenticate(make_user(role, 2 if role == AccountRole.STAFF else 3))

    response = client.get(REPORT_URL.format(resource) + REPORT_QUERY)

    assert response.status_code == 200
    assert response.json()["from"] == REPORT_DATE.isoformat()
    assert response.json()["to"] == REPORT_DATE.isoformat()
    assert response.json()["count"] == 0
    assert response.json()["results"] == []


def test_donation_report_filters_inclusive_dates_and_reports_database_totals(staff_client):
    make_donation(10, donation_date=date(2026, 11, 3), quantity_units=4)
    make_donation(11, donation_date=REPORT_DATE, quantity_units=2)
    make_donation(12, donation_date=date(2026, 11, 5), quantity_units=8)

    response = staff_client.get(
        REPORT_URL.format("donations")
        + f"?from={REPORT_DATE.isoformat()}&to={REPORT_DATE.isoformat()}&component=RBC&blood_group=A%2B"
    )

    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 1
    assert body["totals"] == {"records": 1, "quantity_units": 2}
    assert body["results"] == [{
        "date": REPORT_DATE.isoformat(),
        "blood_group": "A+",
        "component": "RBC",
        "quantity_units": 2,
        "status": "COMPLETED",
    }]


def test_datetime_report_uses_blood_bank_local_inclusive_date_boundaries(staff_client):
    donation = make_donation(13)
    at_start = make_unit(
        donation, 13,
        collected_at=datetime(2026, 11, 4, 0, 0, tzinfo=LOCAL_ZONE),
    )
    at_end = make_unit(
        donation, 14,
        collected_at=datetime(2026, 11, 4, 23, 59, tzinfo=LOCAL_ZONE),
    )
    outside = make_unit(
        donation, 15,
        collected_at=datetime(2026, 11, 5, 0, 0, tzinfo=LOCAL_ZONE),
    )
    for index, unit in enumerate((at_start, at_end, outside), start=13):
        with patch("django.utils.timezone.now", return_value=unit.collected_at):
            InventoryTransaction.objects.create(
                blood_unit=unit,
                action=InventoryTransaction.Action.ISSUE,
                from_status=BloodUnit.Status.RESERVED,
                to_status=BloodUnit.Status.ISSUED,
                reason="Report test fixture",
            )

    response = staff_client.get(REPORT_URL.format("inventory") + REPORT_QUERY)

    assert response.status_code == 200
    assert response.json()["count"] == 2
    assert response.json()["totals"]["quantity_units"] == 2


def test_request_report_omits_personal_and_clinical_identifiers(staff_client):
    request = make_request(16)

    response = staff_client.get(REPORT_URL.format("requests") + REPORT_QUERY)

    assert response.status_code == 200
    assert response.json()["count"] == 1
    serialized = str(response.json())
    assert request.request_id in serialized
    assert request.patient_name not in serialized
    assert request.contact_phone not in serialized
    assert request.hospital not in serialized
    assert "Private Patient" not in serialized


def test_issued_units_report_uses_issued_allocations_and_quantity_totals(staff_client):
    donation = make_donation(17, quantity_units=3)
    unit = make_unit(donation, 17, quantity_units=3)
    request = make_request(17)
    allocation = BloodAllocation.objects.create(
        blood_request=request,
        blood_unit=unit,
        status=BloodAllocation.Status.ISSUED,
        issued_at=timezone.now(),
    )
    BloodAllocation.objects.filter(pk=allocation.pk).update(
        issued_at=datetime(2026, 11, 4, 10, 0, tzinfo=LOCAL_ZONE),
    )

    response = staff_client.get(REPORT_URL.format("issued-units") + REPORT_QUERY)

    assert response.status_code == 200
    assert response.json()["count"] == 1
    assert response.json()["totals"] == {"records": 1, "quantity_units": 3}
    assert response.json()["results"][0]["request_id"] == request.request_id


def test_request_and_issued_reports_apply_local_date_bounds_and_resource_filters(staff_client):
    included_request = make_request(18)
    make_request(19, created_at=datetime(2026, 11, 5, 0, 0, tzinfo=LOCAL_ZONE))
    donation = make_donation(18)
    inside_unit = make_unit(donation, 18)
    outside_unit = make_unit(donation, 19)
    inside_allocation = BloodAllocation.objects.create(
        blood_request=included_request,
        blood_unit=inside_unit,
        status=BloodAllocation.Status.ISSUED,
        issued_at=datetime(2026, 11, 4, 12, 0, tzinfo=LOCAL_ZONE),
    )
    BloodAllocation.objects.create(
        blood_request=included_request,
        blood_unit=outside_unit,
        status=BloodAllocation.Status.ISSUED,
        issued_at=datetime(2026, 11, 5, 0, 0, tzinfo=LOCAL_ZONE),
    )

    request_report = staff_client.get(
        REPORT_URL.format("requests") + REPORT_QUERY + "&status=PENDING&urgency=URGENT"
    )
    issued_report = staff_client.get(
        REPORT_URL.format("issued-units") + REPORT_QUERY + "&component=RBC&blood_group=A%2B"
    )

    assert request_report.status_code == 200
    assert request_report.json()["count"] == 1
    assert request_report.json()["results"][0]["request_id"] == included_request.request_id
    assert issued_report.status_code == 200
    assert issued_report.json()["count"] == 1
    assert issued_report.json()["results"][0]["request_id"] == included_request.request_id
    assert str(inside_allocation.pk) not in str(issued_report.json())


def test_json_results_are_paginated_and_page_size_is_capped_at_100(staff_client):
    sample = make_donation(20)
    for _ in range(102):
        Donation.objects.create(
            donor=sample.donor,
            donation_date=REPORT_DATE,
            blood_group="A+",
            component=Donation.Component.RBC,
            quantity_units=1,
            screening_weight_kg="65.00",
        )

    first_page = staff_client.get(
        REPORT_URL.format("donations") + REPORT_QUERY + "&page=1&page_size=10"
    )
    oversized_page = staff_client.get(
        REPORT_URL.format("donations") + REPORT_QUERY + "&page=1&page_size=101"
    )

    assert first_page.status_code == 200
    assert first_page.json()["count"] == 103
    assert len(first_page.json()["results"]) == 10
    assert oversized_page.status_code == 200
    assert oversized_page.json()["page_size"] == 100
    assert len(oversized_page.json()["results"]) == 100


def test_csv_export_matches_filtered_result_and_is_valid_csv(staff_client):
    make_donation(123, quantity_units=2)
    make_donation(124, component=Donation.Component.PLASMA, quantity_units=5)
    filtered = "&component=RBC&blood_group=A%2B"
    json_response = staff_client.get(REPORT_URL.format("donations") + REPORT_QUERY + filtered)
    csv_response = staff_client.get(
        REPORT_URL.format("donations") + REPORT_QUERY + filtered + "&export=csv"
    )

    assert json_response.status_code == csv_response.status_code == 200
    csv_rows = list(
        csv.DictReader(StringIO(b"".join(csv_response.streaming_content).decode("utf-8")))
    )
    assert len(csv_rows) == json_response.json()["count"] == 1
    assert csv_rows[0]["quantity_units"] == str(json_response.json()["results"][0]["quantity_units"])
    assert "text/csv" in csv_response["Content-Type"]
    assert "attachment;" in csv_response["Content-Disposition"]


@pytest.mark.parametrize(
    "query",
    [
        "?from=2026-11-04",
        "?from=2026-02-30&to=2026-11-04",
        "?from=2026-11-05&to=2026-11-04",
        "?from=2026-11-04&to=2026-11-04&page=0",
        "?from=2026-11-04&to=2026-11-04&page_size=abc",
        "?from=2026-11-04&to=2026-11-04&component=SQL",
        "?from=2026-11-04&to=2026-11-04&unexpected=value",
        "?from=2026-11-04&to=2026-11-04&export=xml",
    ],
)
def test_invalid_report_inputs_return_field_errors(staff_client, query):
    response = staff_client.get(REPORT_URL.format("donations") + query)

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "validation_error"
    assert response.json()["error"]["details"]


def test_reports_require_authentication_and_an_allowed_role():
    assert APIClient().get(REPORT_URL.format("donations") + REPORT_QUERY).status_code == 401
    donor_client = APIClient()
    donor_client.force_authenticate(make_user(AccountRole.DONOR, 130))
    assert donor_client.get(REPORT_URL.format("donations") + REPORT_QUERY).status_code == 403


def test_admin_gets_grouped_summaries_without_staff_level_record_access():
    donation = make_donation(131, quantity_units=3)
    unit = make_unit(donation, 131, quantity_units=3)
    with patch(
        "django.utils.timezone.now",
        return_value=datetime(2026, 11, 4, 12, 0, tzinfo=LOCAL_ZONE),
    ):
        InventoryTransaction.objects.create(
            blood_unit=unit,
            action=InventoryTransaction.Action.ISSUE,
            from_status=BloodUnit.Status.RESERVED,
            to_status=BloodUnit.Status.ISSUED,
            reason="Report test fixture",
        )
    request = make_request(132)
    BloodAllocation.objects.create(
        blood_request=request,
        blood_unit=unit,
        status=BloodAllocation.Status.ISSUED,
        issued_at=datetime(2026, 11, 4, 12, 0, tzinfo=LOCAL_ZONE),
    )
    client = APIClient()
    client.force_authenticate(make_user(AccountRole.ADMIN, 131))

    donation_report = client.get(REPORT_URL.format("donations") + REPORT_QUERY).json()
    inventory_report = client.get(REPORT_URL.format("inventory") + REPORT_QUERY).json()
    request_report = client.get(REPORT_URL.format("requests") + REPORT_QUERY).json()
    issued_report = client.get(REPORT_URL.format("issued-units") + REPORT_QUERY).json()

    assert donation_report["count"] == 1
    assert donation_report["results"][0]["records"] == 1
    assert donation_report["results"][0]["quantity_units"] == 3
    assert inventory_report["count"] == 1
    assert inventory_report["results"][0]["records"] == 1
    assert "unit_code" not in inventory_report["results"][0]
    assert request_report["count"] == 1
    assert request_report["results"][0]["records"] == 1
    assert "request_id" not in request_report["results"][0]
    assert "patient_name" not in request_report["results"][0]
    assert issued_report["count"] == 1
    assert issued_report["results"][0]["records"] == 1
    assert "request_id" not in issued_report["results"][0]


def test_admin_csv_contains_same_grouped_filtered_rows_as_json():
    make_donation(140, quantity_units=2)
    make_donation(141, quantity_units=3)
    client = APIClient()
    client.force_authenticate(make_user(AccountRole.ADMIN, 140))

    filtered = "&component=RBC&blood_group=A%2B"
    json_report = client.get(REPORT_URL.format("donations") + REPORT_QUERY + filtered)
    csv_report = client.get(
        REPORT_URL.format("donations") + REPORT_QUERY + filtered + "&export=csv"
    )
    rows = list(
        csv.DictReader(StringIO(b"".join(csv_report.streaming_content).decode("utf-8")))
    )

    assert json_report.status_code == csv_report.status_code == 200
    assert len(rows) == json_report.json()["count"] == 1
    assert rows[0]["records"] == "2"
    assert rows[0]["quantity_units"] == str(json_report.json()["results"][0]["quantity_units"])
    assert "request_id" not in rows[0]


def test_unknown_report_type_is_not_found(staff_client):
    response = staff_client.get(REPORT_URL.format("users") + REPORT_QUERY)

    assert response.status_code == 404
