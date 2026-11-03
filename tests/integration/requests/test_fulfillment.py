from datetime import date, timedelta
from decimal import Decimal
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError, connection, transaction, close_old_connections
from django.utils import timezone
from rest_framework.test import APIClient

from apps.audit.models import AuditEvent
from apps.donors.models import Donation, DonorProfile
from apps.inventory.models import BloodUnit, InventoryTransaction
from apps.inventory.services import BloodUnitRejected
from apps.notifications.models import Notification
from apps.requests.models import BloodAllocation, BloodRequest, IssueIdempotency
from apps.requests.services import BloodRequestRejected


pytestmark = pytest.mark.django_db

PASSWORD = "Synthetic-Test-Password-532!"
REQUEST_URL = "/api/v1/requests/{request_id}"


def make_user(role, index=1):
    email = f"{role.lower()}-fulfillment-{index}@example.test"
    phone_suffix = {"DONOR": 1000, "RECIPIENT": 3000, "STAFF": 5000, "ADMIN": 7000}[role] + index
    return get_user_model().objects.create_user(
        username=email,
        email=email,
        phone=f"+1202555{phone_suffix:04d}",
        role=role,
        password=PASSWORD,
    )


def make_request(*, staff=None, index=1, status=BloodRequest.Status.APPROVED,
                 patient_blood_group="A+", component="RBC", units_needed=2):
    recipient = make_user("RECIPIENT", index)
    staff = staff or make_user("STAFF", index + 100)
    return BloodRequest.objects.create(
        request_id=f"REQ-FULFILL-{index:04d}",
        requester=recipient,
        patient_name="Synthetic Patient",
        patient_blood_group=patient_blood_group,
        component=component,
        units_needed=units_needed,
        urgency=BloodRequest.Urgency.URGENT,
        hospital="Synthetic General Hospital",
        required_by=timezone.now() + timedelta(days=1),
        contact_phone="+12025550199",
        status=status,
        reviewer=None if status == BloodRequest.Status.PENDING else staff,
        reviewed_at=None if status == BloodRequest.Status.PENDING else timezone.now(),
    )


def make_unit(*, index, blood_group="A+", component="RBC", expiry_days=10,
              quantity_units=1, status=BloodUnit.Status.AVAILABLE):
    donor = make_user("DONOR", index + 200)
    profile = DonorProfile.objects.create(
        user=donor,
        birth_date=date(1990, 1, 1),
        weight_kg=Decimal("62.00"),
        blood_group=blood_group,
    )
    collected_at = timezone.now() - timedelta(days=1)
    donation = Donation.objects.create(
        donor=profile,
        donation_date=collected_at.date(),
        blood_group=blood_group,
        component=Donation.Component.WHOLE_BLOOD,
        quantity_units=1,
        status=Donation.Status.COMPLETED,
        screening_weight_kg=Decimal("62.00"),
    )
    return BloodUnit.objects.create(
        donation=donation,
        unit_code=f"BB-FULFILL-{index:04d}",
        blood_group=blood_group,
        component=component,
        collected_at=collected_at,
        expiry_date=timezone.localdate() + timedelta(days=expiry_days),
        quantity_units=quantity_units,
        status=status,
    )


def client_as(user):
    client = APIClient()
    client.force_authenticate(user)
    return client


def endpoint(blood_request, action):
    return f"{REQUEST_URL.format(request_id=blood_request.request_id)}/{action}"


def reserve(client, blood_request):
    return client.post(endpoint(blood_request, "reserve"), {}, format="json")


def issue(client, blood_request, key="fulfill-retry-001"):
    return client.post(
        endpoint(blood_request, "issue"),
        {},
        format="json",
        HTTP_IDEMPOTENCY_KEY=key,
    )


def test_reservation_prefers_exact_group_then_uses_fefo_and_writes_side_effects():
    staff = make_user("STAFF")
    blood_request = make_request(staff=staff)
    exact_later = make_unit(index=1, blood_group="A+", expiry_days=9)
    compatible_early = make_unit(index=2, blood_group="A-", expiry_days=2)
    compatible_latest = make_unit(index=3, blood_group="O-", expiry_days=4)

    response = reserve(client_as(staff), blood_request)

    assert response.status_code == 200, response.content
    assert [row["id"] for row in response.json()["reserved_units"]] == [
        str(exact_later.pk),
        str(compatible_early.pk),
    ]
    blood_request.refresh_from_db()
    assert blood_request.status == BloodRequest.Status.RESERVED
    assert set(BloodAllocation.objects.filter(blood_request=blood_request).values_list(
        "blood_unit_id", flat=True
    )) == {exact_later.pk, compatible_early.pk}
    assert exact_later.transactions.get().action == InventoryTransaction.Action.RESERVE
    assert compatible_early.transactions.get().action == InventoryTransaction.Action.RESERVE
    assert compatible_latest.status == BloodUnit.Status.AVAILABLE
    assert AuditEvent.objects.filter(action="REQUEST_RESERVED", actor=staff).count() == 1
    assert AuditEvent.objects.filter(action="UNIT_RESERVED", actor=staff).count() == 2
    assert Notification.objects.filter(
        blood_request=blood_request,
        type=Notification.Type.REQUEST_RESERVED,
    ).count() == 1


def test_insufficient_stock_rolls_back_every_reservation_side_effect():
    staff = make_user("STAFF")
    blood_request = make_request(staff=staff, units_needed=3)
    unit = make_unit(index=10, blood_group="A+", expiry_days=3)

    response = reserve(client_as(staff), blood_request)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "insufficient_stock"
    blood_request.refresh_from_db()
    unit.refresh_from_db()
    assert blood_request.status == BloodRequest.Status.APPROVED
    assert unit.status == BloodUnit.Status.AVAILABLE
    assert BloodAllocation.objects.count() == 0
    assert InventoryTransaction.objects.count() == 0
    assert not AuditEvent.objects.filter(action__in=("REQUEST_RESERVED", "UNIT_RESERVED")).exists()
    assert Notification.objects.count() == 0


def test_failure_during_second_reserve_transition_rolls_back_first_unit_everywhere():
    staff = make_user("STAFF")
    blood_request = make_request(staff=staff, index=5)
    units = [make_unit(index=5), make_unit(index=6)]
    from apps.requests import services as request_services

    real_transition = request_services.transition_blood_unit
    calls = 0

    def fail_on_second(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise BloodUnitRejected(
                "unit_unavailable", "Synthetic locked-transition failure.", status_code=409
            )
        return real_transition(*args, **kwargs)

    with patch.object(request_services, "transition_blood_unit", side_effect=fail_on_second):
        response = reserve(client_as(staff), blood_request)

    assert response.status_code == 409
    blood_request.refresh_from_db()
    assert blood_request.status == BloodRequest.Status.APPROVED
    for unit in units:
        unit.refresh_from_db()
        assert unit.status == BloodUnit.Status.AVAILABLE
    assert BloodAllocation.objects.count() == 0
    assert InventoryTransaction.objects.count() == 0
    assert not AuditEvent.objects.filter(action__in=("REQUEST_RESERVED", "UNIT_RESERVED")).exists()
    assert not Notification.objects.exists()


def test_incompatible_stock_is_rejected_without_partial_records():
    staff = make_user("STAFF")
    blood_request = make_request(staff=staff, patient_blood_group="O-", units_needed=1)
    unit = make_unit(index=11, blood_group="AB+", expiry_days=5)

    response = reserve(client_as(staff), blood_request)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "incompatible_blood_type"
    unit.refresh_from_db()
    assert unit.status == BloodUnit.Status.AVAILABLE
    assert blood_request.status == BloodRequest.Status.APPROVED
    assert BloodAllocation.objects.count() == 0
    assert InventoryTransaction.objects.count() == 0
    assert not Notification.objects.exists()


@pytest.mark.parametrize("role", ["DONOR", "RECIPIENT", "ADMIN"])
def test_non_staff_cannot_reserve_or_issue(role):
    blood_request = make_request(index=20)
    unit = make_unit(index=20, blood_group="A+")
    actor = make_user(role, 30)

    reserve_response = reserve(client_as(actor), blood_request)
    issue_response = issue(client_as(actor), blood_request)

    assert reserve_response.status_code == issue_response.status_code == 403
    blood_request.refresh_from_db()
    unit.refresh_from_db()
    assert blood_request.status == BloodRequest.Status.APPROVED
    assert unit.status == BloodUnit.Status.AVAILABLE
    assert BloodAllocation.objects.count() == 0
    assert InventoryTransaction.objects.count() == 0


def test_reservation_requires_approved_request_and_enough_eligible_units():
    staff = make_user("STAFF")
    blood_request = make_request(staff=staff, status=BloodRequest.Status.PENDING)
    make_unit(index=31)

    response = reserve(client_as(staff), blood_request)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "invalid_state_transition"
    assert BloodAllocation.objects.count() == 0
    assert InventoryTransaction.objects.count() == 0


def test_issue_rechecks_expiry_before_transition_and_rolls_back_without_partial_issue():
    staff = make_user("STAFF")
    blood_request = make_request(staff=staff, index=40)
    first = make_unit(index=40, expiry_days=5)
    second = make_unit(index=41, expiry_days=6)
    client = client_as(staff)
    assert reserve(client, blood_request).status_code == 200

    second.expiry_date = timezone.localdate()
    second.save(update_fields=("expiry_date",))
    before_transactions = InventoryTransaction.objects.count()
    before_notifications = Notification.objects.count()

    response = issue(client, blood_request)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "unit_unavailable"
    blood_request.refresh_from_db()
    first.refresh_from_db()
    second.refresh_from_db()
    assert blood_request.status == BloodRequest.Status.RESERVED
    assert first.status == second.status == BloodUnit.Status.RESERVED
    assert set(BloodAllocation.objects.values_list("status", flat=True)) == {
        BloodAllocation.Status.RESERVED
    }
    assert InventoryTransaction.objects.count() == before_transactions
    assert Notification.objects.count() == before_notifications
    assert not IssueIdempotency.objects.exists()
    assert not AuditEvent.objects.filter(action="REQUEST_FULFILLED").exists()


def test_issue_rechecks_compatibility_inside_fulfillment_and_rolls_back():
    staff = make_user("STAFF")
    blood_request = make_request(staff=staff, index=45)
    first = make_unit(index=45, blood_group="A+", expiry_days=5)
    second = make_unit(index=46, blood_group="A-", expiry_days=6)
    client = client_as(staff)
    assert reserve(client, blood_request).status_code == 200

    second.blood_group = "B-"
    second.save(update_fields=("blood_group",))
    before_transactions = InventoryTransaction.objects.count()
    response = issue(client, blood_request)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "incompatible_blood_type"
    blood_request.refresh_from_db()
    first.refresh_from_db()
    second.refresh_from_db()
    assert blood_request.status == BloodRequest.Status.RESERVED
    assert first.status == second.status == BloodUnit.Status.RESERVED
    assert InventoryTransaction.objects.count() == before_transactions
    assert not IssueIdempotency.objects.exists()


def test_issue_transition_failure_rolls_back_all_units_and_request_side_effects():
    staff = make_user("STAFF")
    blood_request = make_request(staff=staff, index=50)
    units = [make_unit(index=50), make_unit(index=51)]
    client = client_as(staff)
    assert reserve(client, blood_request).status_code == 200
    before_transactions = InventoryTransaction.objects.count()
    before_notifications = Notification.objects.count()
    from apps.requests import services as request_services

    real_transition = request_services.transition_blood_unit
    calls = 0

    def fail_on_second(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise BloodRequestRejected(
                "unit_unavailable", "Synthetic locked-transition failure.", status_code=409
            )
        return real_transition(*args, **kwargs)

    with patch.object(request_services, "transition_blood_unit", side_effect=fail_on_second):
        response = issue(client, blood_request, key="rollback-issue-001")

    assert response.status_code == 409
    blood_request.refresh_from_db()
    assert blood_request.status == BloodRequest.Status.RESERVED
    for unit in units:
        unit.refresh_from_db()
        assert unit.status == BloodUnit.Status.RESERVED
    assert set(BloodAllocation.objects.values_list("status", flat=True)) == {
        BloodAllocation.Status.RESERVED
    }
    assert InventoryTransaction.objects.count() == before_transactions
    assert Notification.objects.count() == before_notifications
    assert not IssueIdempotency.objects.exists()
    assert not AuditEvent.objects.filter(action="REQUEST_FULFILLED").exists()


def test_successful_issue_and_same_key_retry_return_original_without_duplicate_stock_changes():
    staff = make_user("STAFF")
    blood_request = make_request(staff=staff, index=60)
    units = [make_unit(index=60), make_unit(index=61)]
    client = client_as(staff)
    assert reserve(client, blood_request).status_code == 200

    first = issue(client, blood_request, key="issue-request-60")
    retry = issue(client, blood_request, key="issue-request-60")

    assert first.status_code == retry.status_code == 200
    assert first.json() == retry.json()
    assert first.json()["request_id"] == blood_request.request_id
    assert first.json()["status"] == BloodRequest.Status.FULFILLED
    assert {row["id"] for row in first.json()["issued_units"]} == {
        str(unit.pk) for unit in units
    }
    blood_request.refresh_from_db()
    assert blood_request.status == BloodRequest.Status.FULFILLED
    assert set(BloodAllocation.objects.values_list("status", flat=True)) == {
        BloodAllocation.Status.ISSUED
    }
    for unit in units:
        unit.refresh_from_db()
        assert unit.status == BloodUnit.Status.ISSUED
    assert InventoryTransaction.objects.filter(action=InventoryTransaction.Action.ISSUE).count() == 2
    assert AuditEvent.objects.filter(action="UNIT_ISSUED").count() == 2
    assert AuditEvent.objects.filter(action="REQUEST_FULFILLED").count() == 1
    assert Notification.objects.filter(
        blood_request=blood_request,
        type=Notification.Type.REQUEST_FULFILLED,
    ).count() == 1
    assert IssueIdempotency.objects.filter(
        blood_request=blood_request,
        key="issue-request-60",
    ).count() == 1


def test_approved_request_reservation_and_issue_reconcile_all_records_end_to_end():
    staff = make_user("STAFF", 65)
    blood_request = make_request(
        staff=staff,
        index=65,
        status=BloodRequest.Status.PENDING,
        units_needed=1,
    )
    unit = make_unit(index=65, blood_group="A+", expiry_days=8)
    client = client_as(staff)

    approval = client.post(
        endpoint(blood_request, "decision"),
        {"decision": "APPROVE"},
        format="json",
    )
    assert approval.status_code == 200
    reservation = reserve(client, blood_request)
    assert reservation.status_code == 200
    issuance = issue(client, blood_request, key="e2e-request-65")
    assert issuance.status_code == 200

    blood_request.refresh_from_db()
    unit.refresh_from_db()
    allocation = BloodAllocation.objects.get(
        blood_request=blood_request,
        blood_unit=unit,
    )
    assert blood_request.status == BloodRequest.Status.FULFILLED
    assert unit.status == BloodUnit.Status.ISSUED
    assert allocation.status == BloodAllocation.Status.ISSUED
    assert allocation.issued_at is not None
    assert list(
        InventoryTransaction.objects.filter(blood_unit=unit).values_list(
            "action", "from_status", "to_status"
        )
    ) == [
        (InventoryTransaction.Action.RESERVE, "AVAILABLE", "RESERVED"),
        (InventoryTransaction.Action.ISSUE, "RESERVED", "ISSUED"),
    ]
    assert set(
        AuditEvent.objects.filter(entity_id=str(blood_request.pk)).values_list(
            "action", flat=True
        )
    ) == {"REQUEST_APPROVED", "REQUEST_RESERVED", "REQUEST_FULFILLED"}
    assert Notification.objects.filter(blood_request=blood_request).count() == 3
    assert IssueIdempotency.objects.filter(blood_request=blood_request).count() == 1


@pytest.mark.parametrize("key", ["", " " , "x" * 129])
def test_issue_requires_a_nonempty_bounded_idempotency_key(key):
    staff = make_user("STAFF")
    blood_request = make_request(staff=staff, index=70)
    blood_request.units_needed = 1
    blood_request.save(update_fields=("units_needed",))
    make_unit(index=70)
    client = client_as(staff)
    assert reserve(client, blood_request).status_code == 200

    response = issue(client, blood_request, key=key)

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_idempotency_key"
    blood_request.refresh_from_db()
    assert blood_request.status == BloodRequest.Status.RESERVED
    assert not IssueIdempotency.objects.exists()


def test_active_allocation_constraint_prevents_a_second_request_claiming_same_unit():
    staff = make_user("STAFF")
    first_request = make_request(staff=staff, index=80, units_needed=1)
    second_request = make_request(staff=staff, index=81, units_needed=1)
    unit = make_unit(index=80)
    BloodAllocation.objects.create(
        blood_request=first_request,
        blood_unit=unit,
        status=BloodAllocation.Status.RESERVED,
    )

    with pytest.raises(IntegrityError), transaction.atomic():
        BloodAllocation.objects.create(
            blood_request=second_request,
            blood_unit=unit,
            status=BloodAllocation.Status.RESERVED,
        )


@pytest.mark.django_db(transaction=True)
@pytest.mark.skipif(
    not connection.features.has_select_for_update,
    reason="Concurrent row-lock behavior requires PostgreSQL.",
)
def test_concurrent_requests_cannot_reserve_the_same_unit():
    staff = make_user("STAFF", 90)
    first_request = make_request(staff=staff, index=90, units_needed=1)
    second_request = make_request(staff=staff, index=91, units_needed=1)
    make_unit(index=90)
    barrier = Barrier(2)

    def send_reservation(request_id):
        close_old_connections()
        try:
            client = APIClient()
            client.force_authenticate(staff)
            barrier.wait(timeout=5)
            return client.post(
                f"/api/v1/requests/{request_id}/reserve",
                {},
                format="json",
            ).status_code
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as executor:
        statuses = list(executor.map(
            send_reservation,
            (first_request.request_id, second_request.request_id),
        ))

    assert sorted(statuses) == [200, 409]
    assert BloodAllocation.objects.filter(status=BloodAllocation.Status.RESERVED).count() == 1
