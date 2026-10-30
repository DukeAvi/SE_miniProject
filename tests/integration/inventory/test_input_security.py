"""TC-Sec-03: inventory rejects malformed and injection-shaped API input."""

import pytest

from apps.audit.models import AuditEvent
from apps.inventory.models import BloodUnit, InventoryTransaction
from tests.integration.inventory.test_unit_creation import client_as, completed_donation, payload, user


pytestmark = pytest.mark.django_db


@pytest.mark.parametrize("field,value", [
    ("donation_id", ["00000000-0000-4000-8000-000000000001"]),
    ("blood_group", True),
    ("component", {"unsafe": "RBC"}),
    ("collected_at", 1720000000),
    ("expiry_date", ["2026-11-26"]),
    ("quantity_units", "1"),
    ("quantity_units", True),
    ("quantity_units", 1.5),
    ("unit_code", "X'; DROP TABLE inventory_bloodunit; --"),
    ("unit_code", "{{ user.password }}"),
    ("extra", "<script>alert(1)</script>"),
])
def test_unit_creation_rejects_bad_types_and_payloads_without_writes(field, value):
    donation = completed_donation()
    request = payload(donation)
    request[field] = value

    response = client_as(user("STAFF", 700)).post("/api/v1/inventory/units", request, format="json")

    assert response.status_code == 400
    assert BloodUnit.objects.count() == 0
    assert not AuditEvent.objects.filter(action="UNIT_CREATED").exists()


@pytest.mark.parametrize("reason", [True, 4, ["discard"], {"text": "discard"}])
def test_transition_rejects_non_string_reason_without_writes(reason):
    response = client_as(user("STAFF", 701)).post(
        "/api/v1/inventory/units/00000000-0000-4000-8000-000000000001/discard",
        {"reason": reason}, format="json",
    )

    assert response.status_code == 400
    assert InventoryTransaction.objects.count() == 0
    assert not AuditEvent.objects.filter(action="UNIT_DISCARDED").exists()


@pytest.mark.parametrize("filter_name,filter_value", [
    ("blood_group", "O+' OR 1=1 --"),
    ("component", "{{unsafe}}"),
    ("status", "<script>alert(1)</script>"),
])
def test_search_rejects_injection_shaped_filters(filter_name, filter_value):
    response = client_as(user("STAFF", 702)).get(
        "/api/v1/inventory/units", {filter_name: filter_value}
    )

    assert response.status_code == 400
    assert filter_name in response.json()["error"]["details"]
    assert BloodUnit.objects.count() == 0
