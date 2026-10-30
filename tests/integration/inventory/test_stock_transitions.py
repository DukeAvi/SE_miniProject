from datetime import date, datetime, time, timezone
from decimal import Decimal
from threading import Barrier
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import connection
from django.db.utils import NotSupportedError
from rest_framework.test import APIClient

from apps.audit.models import AuditEvent
from apps.donors.models import Donation, DonorProfile
from apps.inventory.models import BloodUnit, InventoryTransaction
from apps.inventory.services import (
    BloodUnitRejected,
    available_stock_count,
    transition_blood_unit,
)


pytestmark = pytest.mark.django_db
TODAY = date(2026, 10, 30)


def make_user(role, suffix=None):
    suffix = suffix or uuid4().hex[:10]
    email = f"{role.lower()}-{suffix}@example.test"
    return get_user_model().objects.create_user(
        username=email, email=email, password="Safe-Long-Password-532!", role=role
    )


def make_unit(*, status=BloodUnit.Status.AVAILABLE, expiry_date=date(2026, 11, 1)):
    donor = make_user("DONOR")
    profile = DonorProfile.objects.create(
        user=donor,
        birth_date=date(1990, 1, 1),
        weight_kg=Decimal("62.00"),
        blood_group="O+",
    )
    donation = Donation.objects.create(
        donor=profile,
        donation_date=date(2026, 10, 29),
        blood_group="O+",
        component=Donation.Component.WHOLE_BLOOD,
        quantity_units=1,
        status=Donation.Status.COMPLETED,
        screening_weight_kg=Decimal("62.00"),
    )
    return BloodUnit.objects.create(
        donation=donation,
        unit_code=f"BU-{uuid4().hex[:12]}",
        blood_group="O+",
        component=BloodUnit.Component.RBC,
        collected_at=datetime.combine(donation.donation_date, time(10), tzinfo=timezone.utc),
        expiry_date=expiry_date,
        quantity_units=1,
        status=status,
    )


@pytest.mark.parametrize(
    ("initial", "action", "target", "event", "as_of_date"),
    [
        (BloodUnit.Status.AVAILABLE, InventoryTransaction.Action.RESERVE, BloodUnit.Status.RESERVED, "UNIT_RESERVED", TODAY),
        (BloodUnit.Status.RESERVED, InventoryTransaction.Action.RELEASE, BloodUnit.Status.AVAILABLE, "UNIT_RELEASED", TODAY),
        (BloodUnit.Status.RESERVED, InventoryTransaction.Action.ISSUE, BloodUnit.Status.ISSUED, "UNIT_ISSUED", TODAY),
        (BloodUnit.Status.AVAILABLE, InventoryTransaction.Action.EXPIRE, BloodUnit.Status.EXPIRED, "UNIT_EXPIRED", date(2026, 11, 1)),
        (BloodUnit.Status.AVAILABLE, InventoryTransaction.Action.DISCARD, BloodUnit.Status.DISCARDED, "UNIT_DISCARDED", TODAY),
        (BloodUnit.Status.ISSUED, InventoryTransaction.Action.RETURN, BloodUnit.Status.RETURNED, "UNIT_RETURNED", TODAY),
    ],
)
def test_valid_transition_changes_unit_and_appends_ledger_and_audit(initial, action, target, event, as_of_date):
    unit = make_unit(status=initial, expiry_date=date(2026, 11, 1) if action != InventoryTransaction.Action.EXPIRE else TODAY)
    actor = None if action == InventoryTransaction.Action.EXPIRE else make_user("STAFF")

    changed = transition_blood_unit(
        actor=actor,
        unit_id=unit.pk,
        action=action,
        reason="Approved test transition",
        as_of_date=as_of_date,
    )

    unit.refresh_from_db()
    ledger = InventoryTransaction.objects.get(blood_unit=unit)
    assert changed.status == target
    assert unit.status == target
    assert ledger.action == action
    assert ledger.from_status == initial
    assert ledger.to_status == target
    assert ledger.actor == actor
    assert ledger.reason == "Approved test transition"
    assert AuditEvent.objects.filter(action=event, actor=actor).count() == 1


@pytest.mark.parametrize(
    ("status", "action", "expiry_date", "as_of_date", "code"),
    [
        (BloodUnit.Status.RESERVED, InventoryTransaction.Action.RESERVE, date(2026, 11, 1), TODAY, "invalid_state_transition"),
        (BloodUnit.Status.AVAILABLE, InventoryTransaction.Action.ISSUE, date(2026, 11, 1), TODAY, "invalid_state_transition"),
        (BloodUnit.Status.AVAILABLE, InventoryTransaction.Action.RELEASE, date(2026, 11, 1), TODAY, "invalid_state_transition"),
        (BloodUnit.Status.ISSUED, InventoryTransaction.Action.DISCARD, date(2026, 11, 1), TODAY, "invalid_state_transition"),
        (BloodUnit.Status.AVAILABLE, InventoryTransaction.Action.EXPIRE, date(2026, 11, 1), TODAY, "invalid_state_transition"),
        (BloodUnit.Status.AVAILABLE, InventoryTransaction.Action.RESERVE, TODAY, TODAY, "unit_unavailable"),
        (BloodUnit.Status.RESERVED, InventoryTransaction.Action.ISSUE, TODAY, TODAY, "unit_unavailable"),
    ],
)
def test_invalid_transitions_leave_unit_ledger_and_audit_unchanged(status, action, expiry_date, as_of_date, code):
    unit = make_unit(status=status, expiry_date=expiry_date)
    actor = make_user("STAFF")

    with pytest.raises(BloodUnitRejected) as rejected:
        transition_blood_unit(
            actor=actor,
            unit_id=unit.pk,
            action=action,
            reason="Test transition",
            as_of_date=as_of_date,
        )

    unit.refresh_from_db()
    assert rejected.value.code == code
    assert unit.status == status
    assert InventoryTransaction.objects.count() == 0
    assert AuditEvent.objects.count() == 0


def test_transition_rolls_back_unit_and_ledger_when_audit_write_fails():
    unit = make_unit()
    actor = make_user("STAFF")

    with patch("apps.inventory.services.record_event", side_effect=RuntimeError("audit unavailable")):
        with pytest.raises(RuntimeError):
            transition_blood_unit(
                actor=actor,
                unit_id=unit.pk,
                action=InventoryTransaction.Action.DISCARD,
                reason="Damaged packaging",
            )

    unit.refresh_from_db()
    assert unit.status == BloodUnit.Status.AVAILABLE
    assert InventoryTransaction.objects.count() == 0
    assert AuditEvent.objects.count() == 0


def test_inventory_ledger_rejects_update_and_delete():
    unit = make_unit()
    actor = make_user("STAFF")
    entry = transition_blood_unit(
        actor=actor,
        unit_id=unit.pk,
        action=InventoryTransaction.Action.DISCARD,
        reason="Damaged packaging",
    ).transactions.get()

    with pytest.raises(ValidationError):
        entry.save()
    with pytest.raises(ValidationError):
        entry.delete()
    with pytest.raises(NotSupportedError):
        InventoryTransaction.objects.filter(pk=entry.pk).update(reason="changed")
    with pytest.raises(NotSupportedError):
        InventoryTransaction.objects.filter(pk=entry.pk).delete()


def test_available_stock_is_derived_from_status_and_expiry_boundary():
    unexpired = make_unit(expiry_date=date(2026, 10, 31))
    make_unit(expiry_date=TODAY)
    reserved = make_unit(status=BloodUnit.Status.RESERVED, expiry_date=date(2026, 11, 1))
    assert available_stock_count(blood_group="O+", component="RBC", as_of_date=TODAY) == 1

    transition_blood_unit(
        actor=make_user("STAFF"),
        unit_id=unexpired.pk,
        action=InventoryTransaction.Action.RESERVE,
        reason="Allocated to request",
        as_of_date=TODAY,
    )
    assert available_stock_count(blood_group="O+", component="RBC", as_of_date=TODAY) == 0
    assert reserved.status == BloodUnit.Status.RESERVED


def test_staff_can_discard_and_return_units_through_api():
    staff = make_user("STAFF")
    available = make_unit()
    issued = make_unit(status=BloodUnit.Status.ISSUED)
    client = APIClient()
    client.force_authenticate(staff)

    discarded = client.post(
        f"/api/v1/inventory/units/{available.pk}/discard",
        {"reason": "Packaging damaged"},
        format="json",
    )
    returned = client.post(
        f"/api/v1/inventory/units/{issued.pk}/return",
        {"reason": "Not used"},
        format="json",
    )

    assert discarded.status_code == 200
    assert discarded.json()["status"] == BloodUnit.Status.DISCARDED
    assert returned.status_code == 200
    assert returned.json()["status"] == BloodUnit.Status.RETURNED
    assert InventoryTransaction.objects.count() == 2


@pytest.mark.parametrize("role", ["DONOR", "RECIPIENT", "ADMIN"])
def test_non_staff_cannot_discard_or_return_units(role):
    unit = make_unit()
    client = APIClient()
    client.force_authenticate(make_user(role))

    response = client.post(
        f"/api/v1/inventory/units/{unit.pk}/discard",
        {"reason": "Forbidden"},
        format="json",
    )

    assert response.status_code == 403
    unit.refresh_from_db()
    assert unit.status == BloodUnit.Status.AVAILABLE
    assert InventoryTransaction.objects.count() == 0


@pytest.mark.parametrize("payload", [{}, {"reason": "  "}, {"reason": "Bad", "extra": "field"}])
def test_transition_api_rejects_invalid_payload_without_changes(payload):
    unit = make_unit()
    client = APIClient()
    client.force_authenticate(make_user("STAFF"))

    response = client.post(f"/api/v1/inventory/units/{unit.pk}/discard", payload, format="json")

    assert response.status_code == 400
    unit.refresh_from_db()
    assert unit.status == BloodUnit.Status.AVAILABLE
    assert InventoryTransaction.objects.count() == 0


@pytest.mark.skipif(connection.vendor != "postgresql", reason="PostgreSQL row-lock behavior is not available on SQLite")
@pytest.mark.django_db(transaction=True)
def test_concurrent_reservation_cannot_change_the_same_unit_twice():
    unit = make_unit()
    barrier = Barrier(2)
    staff = make_user("STAFF")

    def attempt(_):
        from django.db import close_old_connections
        close_old_connections()
        actor = get_user_model().objects.get(pk=staff.pk)
        barrier.wait()
        try:
            transition_blood_unit(
                actor=actor,
                unit_id=unit.pk,
                action=InventoryTransaction.Action.RESERVE,
                reason="Concurrent reservation test",
            )
            result = "ok"
        except BloodUnitRejected:
            result = "conflict"
        close_old_connections()
        return result

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(attempt, range(2)))

    assert sorted(results) == ["conflict", "ok"]
    assert InventoryTransaction.objects.filter(blood_unit=unit).count() == 1
    assert AuditEvent.objects.count() == 1
