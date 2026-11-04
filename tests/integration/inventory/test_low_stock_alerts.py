from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, time, timezone
from decimal import Decimal
from threading import Barrier
from uuid import uuid4
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.db import connection
from rest_framework.test import APIClient

from apps.audit.models import AuditEvent
from apps.donors.models import Donation, DonorProfile
from apps.inventory.models import (
    BloodUnit,
    InventoryJobRun,
    InventoryTransaction,
    LowStockAlert,
    StockThreshold,
)
from apps.inventory.services import run_inventory_expiry_job, transition_blood_unit
from apps.notifications.models import Notification


pytestmark = pytest.mark.django_db
TODAY = date(2026, 10, 30)
THRESHOLD_URL = "/api/v1/admin/stock-thresholds"


def make_user(role, *, active=True):
    suffix = uuid4().hex[:12]
    email = f"{role.lower()}-lowstock-{suffix}@example.test"
    return get_user_model().objects.create_user(
        username=email,
        email=email,
        password="Safe-Long-Password-532!",
        role=role,
        is_active=active,
    )


def make_unit(*, status=BloodUnit.Status.AVAILABLE, quantity=1, expiry_date=date(2026, 11, 10), group="O+", component="RBC"):
    donor = make_user("DONOR")
    profile = DonorProfile.objects.create(
        user=donor,
        birth_date=date(1990, 1, 1),
        weight_kg=Decimal("62.00"),
        blood_group=group,
    )
    donation = Donation.objects.create(
        donor=profile,
        donation_date=date(2026, 10, 29),
        blood_group=group,
        component=component,
        quantity_units=quantity,
        status=Donation.Status.COMPLETED,
        screening_weight_kg=Decimal("62.00"),
    )
    return BloodUnit.objects.create(
        donation=donation,
        unit_code=f"BU-{uuid4().hex[:12]}",
        blood_group=group,
        component=component,
        collected_at=datetime.combine(
            donation.donation_date, time(10), tzinfo=timezone.utc
        ),
        expiry_date=expiry_date,
        quantity_units=quantity,
        status=status,
    )


def client_as(user):
    client = APIClient()
    client.force_authenticate(user)
    return client


@pytest.fixture(autouse=True)
def freeze_blood_bank_date(monkeypatch):
    monkeypatch.setattr("apps.inventory.services.blood_bank_today", lambda: TODAY)


def test_migration_seeds_default_threshold_for_every_supported_pair():
    thresholds = list(StockThreshold.objects.all())

    assert len(thresholds) == 32
    assert {(row.blood_group, row.component) for row in thresholds} == {
        (group, component)
        for group in StockThreshold.BLOOD_GROUPS
        for component in BloodUnit.Component.values
    }
    assert {row.threshold_units for row in thresholds} == {5}
    assert not any(row.alert_active for row in thresholds)


def test_only_admin_can_read_and_update_thresholds_and_real_changes_are_audited():
    admin = make_user("ADMIN")
    staff = make_user("STAFF")
    admin_client = client_as(admin)
    staff_client = client_as(staff)
    payload = {
        "thresholds": [{
            "blood_group": "O+",
            "component": "RBC",
            "threshold_units": 3,
        }]
    }

    initial = admin_client.get(THRESHOLD_URL)
    forbidden_read = staff_client.get(THRESHOLD_URL)
    updated = admin_client.put(THRESHOLD_URL, payload, format="json")
    forbidden_update = staff_client.put(THRESHOLD_URL, payload, format="json")

    assert initial.status_code == 200
    assert len(initial.json()["thresholds"]) == 32
    assert initial.json()["thresholds"][0]["threshold_units"] == 5
    assert forbidden_read.status_code == forbidden_update.status_code == 403
    assert updated.status_code == 200
    assert updated.json() == payload
    threshold = StockThreshold.objects.get(blood_group="O+", component="RBC")
    assert threshold.threshold_units == 3
    assert AuditEvent.objects.filter(
        action="THRESHOLD_CHANGED", actor=admin, entity_type="STOCK_THRESHOLD"
    ).count() == 1
    admin_client.put(THRESHOLD_URL, payload, format="json")
    assert AuditEvent.objects.filter(action="THRESHOLD_CHANGED", actor=admin).count() == 1


@pytest.mark.parametrize("role", ["DONOR", "RECIPIENT"])
def test_non_admin_roles_cannot_read_or_update_thresholds(role):
    actor = make_user(role)
    client = client_as(actor)
    payload = {"thresholds": [{
        "blood_group": "O+", "component": "RBC", "threshold_units": 2,
    }]}

    read_response = client.get(THRESHOLD_URL)
    write_response = client.put(THRESHOLD_URL, payload, format="json")

    assert read_response.status_code == write_response.status_code == 403
    assert StockThreshold.objects.get(blood_group="O+", component="RBC").threshold_units == 5


@pytest.mark.parametrize(
    "payload",
    [
        {"thresholds": [{"blood_group": "O+", "component": "RBC", "threshold_units": 0}]},
        {"thresholds": [{"blood_group": "X+", "component": "RBC", "threshold_units": 2}]},
        {"thresholds": [{"blood_group": "O+", "component": "SERUM", "threshold_units": 2}]},
        {"thresholds": [
            {"blood_group": "O+", "component": "RBC", "threshold_units": 2},
            {"blood_group": "O+", "component": "RBC", "threshold_units": 3},
        ]},
        {"thresholds": [{"blood_group": "O+", "component": "RBC", "threshold_units": True}]},
        {"thresholds": [{"blood_group": "O+", "component": "RBC", "threshold_units": 2, "extra": 1}]},
        {"thresholds": []},
    ],
)
def test_invalid_threshold_updates_save_nothing(payload):
    admin = make_user("ADMIN")
    before = StockThreshold.objects.get(blood_group="O+", component="RBC").threshold_units

    response = client_as(admin).put(THRESHOLD_URL, payload, format="json")

    assert response.status_code == 400
    assert StockThreshold.objects.get(blood_group="O+", component="RBC").threshold_units == before
    assert not AuditEvent.objects.filter(action="THRESHOLD_CHANGED", actor=admin).exists()


def test_threshold_change_audit_failure_rolls_back_the_value():
    admin = make_user("ADMIN")
    threshold = StockThreshold.objects.get(blood_group="O+", component="RBC")

    with patch(
        "apps.inventory.thresholds.record_event",
        side_effect=RuntimeError("audit unavailable"),
    ), pytest.raises(RuntimeError):
        client_as(admin).put(
            THRESHOLD_URL,
            {"thresholds": [{"blood_group": "O+", "component": "RBC", "threshold_units": 4}]},
            format="json",
        )

    threshold.refresh_from_db()
    assert threshold.threshold_units == 5


def test_alert_crossing_is_atomic_deduplicated_and_resets_after_recovery():
    threshold = StockThreshold.objects.get(blood_group="O+", component="RBC")
    threshold.threshold_units = 2
    threshold.save(update_fields=("threshold_units",))
    staff = [make_user("STAFF"), make_user("STAFF")]
    inactive_staff = make_user("STAFF", active=False)
    available = [make_unit() for _ in range(3)]
    reserved = [make_unit(status=BloodUnit.Status.RESERVED) for _ in range(2)]

    transition_blood_unit(
        actor=staff[0], unit_id=available[0].pk,
        action=InventoryTransaction.Action.DISCARD, reason="Damaged",
    )
    assert LowStockAlert.objects.count() == 0  # exactly at the threshold
    transition_blood_unit(
        actor=staff[0], unit_id=available[1].pk,
        action=InventoryTransaction.Action.DISCARD, reason="Damaged",
    )
    first_alert = LowStockAlert.objects.get()
    assert first_alert.available_units == 1
    assert first_alert.threshold_units == 2
    assert set(Notification.objects.filter(stock_alert=first_alert).values_list(
        "recipient_id", flat=True
    )) == {user.pk for user in staff}
    assert not Notification.objects.filter(recipient=inactive_staff).exists()

    transition_blood_unit(
        actor=staff[0], unit_id=available[2].pk,
        action=InventoryTransaction.Action.DISCARD, reason="Damaged",
    )
    assert LowStockAlert.objects.count() == 1
    assert Notification.objects.filter(type=Notification.Type.LOW_STOCK_ALERT).count() == 2
    staff_notices = client_as(staff[0]).get("/api/v1/notifications")
    assert staff_notices.status_code == 200
    low_stock_notice = next(
        row for row in staff_notices.json()["results"]
        if row["type"] == Notification.Type.LOW_STOCK_ALERT
    )
    assert low_stock_notice["low_stock_alert"] == {
        "blood_group": "O+",
        "component": "RBC",
        "available_units": 1,
        "threshold_units": 2,
    }

    for unit in reserved:
        transition_blood_unit(
            actor=staff[0], unit_id=unit.pk,
            action=InventoryTransaction.Action.RELEASE, reason="Reservation released",
        )
    threshold.refresh_from_db()
    assert not threshold.alert_active  # stock recovered to the threshold

    transition_blood_unit(
        actor=staff[0], unit_id=reserved[0].pk,
        action=InventoryTransaction.Action.DISCARD, reason="Damaged",
    )
    assert LowStockAlert.objects.count() == 2
    assert Notification.objects.filter(type=Notification.Type.LOW_STOCK_ALERT).count() == 4
    assert AuditEvent.objects.filter(action="LOW_STOCK_ALERTED").count() == 2


def test_raising_threshold_can_trigger_alert_and_lowering_it_can_clear_active_state():
    admin = make_user("ADMIN")
    staff = make_user("STAFF")
    threshold = StockThreshold.objects.get(blood_group="O+", component="RBC")
    threshold.threshold_units = 3
    threshold.save(update_fields=("threshold_units",))
    [make_unit() for _ in range(4)]
    payload = {"thresholds": [{
        "blood_group": "O+", "component": "RBC", "threshold_units": 5,
    }]}

    response = client_as(admin).put(THRESHOLD_URL, payload, format="json")

    assert response.status_code == 200
    assert LowStockAlert.objects.count() == 1
    assert Notification.objects.filter(
        type=Notification.Type.LOW_STOCK_ALERT, recipient=staff
    ).count() == 1
    threshold = StockThreshold.objects.get(blood_group="O+", component="RBC")
    assert threshold.alert_active
    payload["thresholds"][0]["threshold_units"] = 4
    client_as(admin).put(THRESHOLD_URL, payload, format="json")
    threshold.refresh_from_db()
    assert not threshold.alert_active
    assert LowStockAlert.objects.count() == 1


def test_daily_expiry_job_evaluates_stock_and_creates_crossing_alert():
    threshold = StockThreshold.objects.get(blood_group="O+", component="RBC")
    threshold.threshold_units = 2
    threshold.save(update_fields=("threshold_units",))
    make_user("STAFF")
    make_unit(expiry_date=TODAY)
    make_unit(expiry_date=date(2026, 11, 1))

    run = run_inventory_expiry_job(as_of_date=TODAY)

    assert run.status == InventoryJobRun.Status.SUCCEEDED
    alert = LowStockAlert.objects.get()
    assert alert.available_units == 1
    assert Notification.objects.filter(stock_alert=alert).count() == 1


def test_alert_failure_rolls_back_the_stock_transition_and_threshold_state():
    threshold = StockThreshold.objects.get(blood_group="O+", component="RBC")
    threshold.threshold_units = 2
    threshold.save(update_fields=("threshold_units",))
    staff = make_user("STAFF")
    unit = make_unit()

    with patch(
        "apps.inventory.thresholds.Notification.objects.create",
        side_effect=RuntimeError("outbox unavailable"),
    ), pytest.raises(RuntimeError):
        transition_blood_unit(
            actor=staff,
            unit_id=unit.pk,
            action=InventoryTransaction.Action.DISCARD,
            reason="Damaged",
        )

    unit.refresh_from_db()
    threshold.refresh_from_db()
    assert unit.status == BloodUnit.Status.AVAILABLE
    assert not threshold.alert_active
    assert InventoryTransaction.objects.count() == 0
    assert LowStockAlert.objects.count() == 0
    assert not AuditEvent.objects.filter(action="LOW_STOCK_ALERTED").exists()


@pytest.mark.skipif(
    connection.vendor != "postgresql",
    reason="PostgreSQL row-lock behavior is not available on SQLite",
)
@pytest.mark.django_db(transaction=True)
def test_concurrent_stock_reductions_create_one_crossing_alert():
    threshold = StockThreshold.objects.get(blood_group="O+", component="RBC")
    threshold.threshold_units = 3
    threshold.save(update_fields=("threshold_units",))
    staff = make_user("STAFF")
    units = [make_unit() for _ in range(4)]
    barrier = Barrier(2)

    def discard(unit_id):
        from django.db import close_old_connections

        close_old_connections()
        actor = get_user_model().objects.get(pk=staff.pk)
        barrier.wait()
        transition_blood_unit(
            actor=actor,
            unit_id=unit_id,
            action=InventoryTransaction.Action.DISCARD,
            reason="Concurrent stock reduction",
        )
        close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(discard, [units[0].pk, units[1].pk]))

    assert LowStockAlert.objects.count() == 1
    assert AuditEvent.objects.filter(action="LOW_STOCK_ALERTED").count() == 1
    assert Notification.objects.filter(type=Notification.Type.LOW_STOCK_ALERT).count() == 1
