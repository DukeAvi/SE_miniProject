from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from io import StringIO
from unittest.mock import patch
from uuid import uuid4

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.utils import timezone as django_timezone
from django.test import override_settings

from apps.audit.models import AuditEvent
from apps.donors.models import Donation, DonorProfile
from apps.inventory.models import BloodUnit, InventoryJobRun, InventoryTransaction
from apps.inventory.monitoring import inventory_expiry_job_health
from apps.inventory.services import (
    EXPIRY_JOB_NAME,
    InventoryExpiryJobFailed,
    run_inventory_expiry_job,
)
from apps.inventory.tasks import expire_eligible_blood_units


pytestmark = pytest.mark.django_db
TODAY = date(2026, 10, 30)


def make_user(role="DONOR"):
    email = f"{role.lower()}-{uuid4().hex[:10]}@example.test"
    return get_user_model().objects.create_user(
        username=email,
        email=email,
        password="Safe-Long-Password-532!",
        role=role,
    )


def make_unit(*, expiry_date, status=BloodUnit.Status.AVAILABLE):
    collection_date = expiry_date - timedelta(days=1)
    donor = make_user()
    profile = DonorProfile.objects.create(
        user=donor,
        birth_date=date(1990, 1, 1),
        weight_kg=Decimal("62.00"),
        blood_group="O+",
    )
    donation = Donation.objects.create(
        donor=profile,
        donation_date=collection_date,
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


@pytest.fixture(autouse=True)
def freeze_blood_bank_date(monkeypatch):
    monkeypatch.setattr("apps.inventory.services.blood_bank_today", lambda: TODAY)


def test_expiry_job_marks_available_and_reserved_units_expired_at_boundary():
    expired_available = make_unit(expiry_date=TODAY)
    expired_reserved = make_unit(expiry_date=TODAY, status=BloodUnit.Status.RESERVED)
    make_unit(expiry_date=TODAY - timedelta(days=1))
    future_available = make_unit(expiry_date=TODAY + timedelta(days=1))
    discarded = make_unit(expiry_date=TODAY, status=BloodUnit.Status.DISCARDED)

    run = run_inventory_expiry_job(as_of_date=TODAY, batch_size=2)

    expired_available.refresh_from_db()
    expired_reserved.refresh_from_db()
    future_available.refresh_from_db()
    discarded.refresh_from_db()
    assert run.status == InventoryJobRun.Status.SUCCEEDED
    assert run.processed_count == 3
    assert run.expired_count == 3
    assert expired_available.status == BloodUnit.Status.EXPIRED
    assert expired_reserved.status == BloodUnit.Status.EXPIRED
    assert future_available.status == BloodUnit.Status.AVAILABLE
    assert discarded.status == BloodUnit.Status.DISCARDED
    assert InventoryTransaction.objects.filter(action=InventoryTransaction.Action.EXPIRE).count() == 3
    assert AuditEvent.objects.filter(action="UNIT_EXPIRED", actor__isnull=True).count() == 3


def test_repeated_successful_run_is_idempotent_for_the_same_date():
    unit = make_unit(expiry_date=TODAY)
    first = run_inventory_expiry_job(as_of_date=TODAY)
    second = run_inventory_expiry_job(as_of_date=TODAY)

    unit.refresh_from_db()
    assert first.pk == second.pk
    assert second.status == InventoryJobRun.Status.SUCCEEDED
    assert second.attempt_count == 1
    assert InventoryTransaction.objects.filter(blood_unit=unit).count() == 1
    assert AuditEvent.objects.filter(action="UNIT_EXPIRED").count() == 1


def test_running_job_for_same_date_is_not_started_again():
    unit = make_unit(expiry_date=TODAY)
    run = InventoryJobRun.objects.create(
        job_name=EXPIRY_JOB_NAME,
        run_date=TODAY,
        status=InventoryJobRun.Status.RUNNING,
        started_at=django_timezone.now(),
    )

    returned = run_inventory_expiry_job(as_of_date=TODAY)

    unit.refresh_from_db()
    assert returned.pk == run.pk
    assert returned.status == InventoryJobRun.Status.RUNNING
    assert unit.status == BloodUnit.Status.AVAILABLE
    assert InventoryTransaction.objects.count() == 0


def test_partial_failure_keeps_committed_batches_and_safe_rerun_finishes_remaining_units():
    [make_unit(expiry_date=TODAY) for _ in range(3)]
    from apps.inventory import services

    actual_batch = services._expire_units_batch
    calls = 0

    def fail_second_batch(unit_ids, *, run, as_of_date):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RuntimeError("synthetic private failure text")
        return actual_batch(unit_ids, run=run, as_of_date=as_of_date)

    with patch("apps.inventory.services._expire_units_batch", side_effect=fail_second_batch):
        with pytest.raises(InventoryExpiryJobFailed):
            run_inventory_expiry_job(as_of_date=TODAY, batch_size=1)

    run = InventoryJobRun.objects.get(job_name=EXPIRY_JOB_NAME, run_date=TODAY)
    assert run.status == InventoryJobRun.Status.FAILED
    assert run.processed_count == 1
    assert run.expired_count == 1
    assert "synthetic private failure text" not in run.error_text
    assert BloodUnit.objects.filter(status=BloodUnit.Status.EXPIRED).count() == 1

    rerun = run_inventory_expiry_job(as_of_date=TODAY, batch_size=1)

    assert rerun.pk == run.pk
    assert rerun.status == InventoryJobRun.Status.SUCCEEDED
    assert rerun.attempt_count == 2
    assert rerun.processed_count == 3
    assert rerun.expired_count == 3
    assert InventoryTransaction.objects.filter(action=InventoryTransaction.Action.EXPIRE).count() == 3


def test_celery_task_accepts_as_of_date_test_hook():
    unit = make_unit(expiry_date=TODAY)

    result = expire_eligible_blood_units.run(as_of_date=TODAY.isoformat())

    unit.refresh_from_db()
    assert result["run_date"] == TODAY.isoformat()
    assert result["status"] == InventoryJobRun.Status.SUCCEEDED
    assert unit.status == BloodUnit.Status.EXPIRED


def test_manual_expiry_command_is_debug_only_and_accepts_test_date():
    with pytest.raises(CommandError, match="DEBUG=True"):
        call_command("run_inventory_expiry", as_of_date=TODAY, stdout=StringIO())

    unit = make_unit(expiry_date=TODAY)
    output = StringIO()
    with override_settings(DEBUG=True):
        call_command("run_inventory_expiry", as_of_date=TODAY, stdout=output)

    unit.refresh_from_db()
    assert "SUCCEEDED" in output.getvalue()
    assert unit.status == BloodUnit.Status.EXPIRED


def test_health_check_detects_missing_failed_and_stale_successful_runs():
    now = django_timezone.now()
    assert inventory_expiry_job_health(now=now) == (False, "No inventory expiry run has been recorded.")

    failed = InventoryJobRun.objects.create(
        job_name=EXPIRY_JOB_NAME,
        run_date=TODAY,
        status=InventoryJobRun.Status.FAILED,
        started_at=now - timedelta(minutes=2),
        finished_at=now,
        error_text="Expiry batch failed; retry is safe.",
    )
    assert inventory_expiry_job_health(now=now)[0] is False
    failed.status = InventoryJobRun.Status.SUCCEEDED
    failed.finished_at = now - timedelta(hours=27)
    failed.save(update_fields=("status", "finished_at"))
    assert inventory_expiry_job_health(now=now) == (
        False,
        "No successful inventory expiry run has completed within 26 hours.",
    )
    failed.finished_at = now - timedelta(hours=25)
    failed.save(update_fields=("finished_at",))
    assert inventory_expiry_job_health(now=now) == (True, "Inventory expiry job is healthy.")


def test_monitor_command_exits_nonzero_for_missing_run_and_succeeds_when_healthy():
    with pytest.raises(CommandError, match="health check failed"):
        call_command("check_inventory_expiry_job", stdout=StringIO(), stderr=StringIO())

    now = django_timezone.now()
    InventoryJobRun.objects.create(
        job_name=EXPIRY_JOB_NAME,
        run_date=TODAY,
        status=InventoryJobRun.Status.SUCCEEDED,
        started_at=now - timedelta(minutes=1),
        finished_at=now,
    )
    output = StringIO()
    call_command("check_inventory_expiry_job", stdout=output)
    assert "healthy" in output.getvalue()


def test_celery_schedule_runs_at_0005_in_the_blood_bank_timezone():
    from bbms.celery import app
    from django.conf import settings

    schedule = settings.CELERY_BEAT_SCHEDULE["expire-blood-units-daily"]
    assert schedule["task"] == "apps.inventory.tasks.expire_eligible_blood_units"
    assert schedule["schedule"].minute == {5}
    assert schedule["schedule"].hour == {0}
    assert app.conf.timezone == settings.BLOOD_BANK_TIME_ZONE


def test_expiry_job_uses_configured_batch_size_when_not_overridden():
    unit = make_unit(expiry_date=TODAY)
    with override_settings(INVENTORY_EXPIRY_BATCH_SIZE=1):
        run = run_inventory_expiry_job(as_of_date=TODAY)
    unit.refresh_from_db()
    assert run.expired_count == 1
    assert unit.status == BloodUnit.Status.EXPIRED
