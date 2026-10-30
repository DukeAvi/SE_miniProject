"""QA-001: repeatable synthetic Sprint 1 dataset and notification mocks."""

import json
from datetime import date, timedelta
from io import StringIO

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import override_settings

from apps.core.demo_mocks import MockNotificationOutbox, REQUEST_STATE_SCENARIOS
from apps.donors.eligibility import check_donor_eligibility
from apps.donors.models import Appointment, Donation, DonationSlot, DonorProfile
from apps.inventory.models import BloodUnit
from apps.notifications.services import MockNotificationAdapter


pytestmark = pytest.mark.django_db
AS_OF_DATE = date(2026, 10, 30)


def run_seed():
    output = StringIO()
    call_command("seed_test_data", as_of_date=AS_OF_DATE, stdout=output)
    return json.loads(output.getvalue().strip().splitlines()[-1])


@override_settings(DEBUG=True)
def test_seed_twice_creates_known_records_and_no_duplicates():
    first = run_seed()
    second = run_seed()

    assert first == second
    assert first == {
        "as_of_date": "2026-10-30",
        "users": 14,
        "profiles": 11,
        "donations": 8,
        "units": 32,
        "slots": 2,
        "appointments": 2,
        "mock_request_states": list(REQUEST_STATE_SCENARIOS),
        "mock_notification_deliveries": 5,
    }
    assert get_user_model().objects.count() == 14
    assert DonorProfile.objects.count() == 11
    assert Donation.objects.count() == 8
    assert BloodUnit.objects.count() == 32
    assert DonationSlot.objects.count() == 2
    assert Appointment.objects.count() == 2
    assert set(get_user_model().objects.values_list("role", flat=True)) == {"DONOR", "RECIPIENT", "STAFF", "ADMIN"}
    assert all(not account.has_usable_password() for account in get_user_model().objects.all())
    assert all(account.email.endswith("@example.test") for account in get_user_model().objects.all())


@override_settings(DEBUG=True)
def test_seed_covers_inventory_and_eligibility_boundaries():
    run_seed()
    assert set(BloodUnit.objects.values_list("blood_group", flat=True)) == {"O-", "O+", "A-", "A+", "B-", "B+", "AB-", "AB+"}
    assert set(BloodUnit.objects.values_list("component", flat=True)) == {"WHOLE_BLOOD", "RBC", "PLASMA", "PLATELETS"}
    assert BloodUnit.objects.filter(status="EXPIRED", expiry_date=AS_OF_DATE).count() == 1
    assert BloodUnit.objects.filter(status="AVAILABLE", expiry_date=AS_OF_DATE + timedelta(days=1)).count() == 1
    assert set(Appointment.objects.values_list("status", flat=True)) == {"BOOKED", "CANCELLED"}

    profiles = {
        label: DonorProfile.objects.get(user__email=f"seed-boundary-{label}@example.test")
        for label in ("age", "weight", "interval")
    }
    results = {
        label: check_donor_eligibility(
            birth_date=profile.birth_date,
            weight_kg=profile.weight_kg,
            on_date=AS_OF_DATE,
            last_whole_blood_donation=profile.last_donation_date,
        )
        for label, profile in profiles.items()
    }
    assert results["age"].eligible
    assert {failure["rule"] for failure in results["weight"].failed_rules} == {"MINIMUM_WEIGHT"}
    assert {failure["rule"] for failure in results["interval"].failed_rules} == {"MINIMUM_INTERVAL"}


def test_mock_outbox_records_delivery_and_failure_without_provider():
    delivered = MockNotificationOutbox()
    for state in REQUEST_STATE_SCENARIOS:
        delivered.enqueue(f"REQUEST_{state}")
    delivered.deliver_pending()
    delivered.deliver_pending()
    assert [event.status for event in delivered.events] == ["DELIVERED"] * 5
    assert delivered.adapter.delivered_events == [f"REQUEST_{state}" for state in REQUEST_STATE_SCENARIOS]

    failed = MockNotificationOutbox(MockNotificationAdapter(fail=True))
    failed.enqueue("REQUEST_APPROVED")
    failed.deliver_pending()
    assert failed.events[0].status == "FAILED"
    assert failed.adapter.delivered_events == []


@override_settings(DEBUG=False)
def test_seed_command_refuses_non_demo_settings():
    with pytest.raises(CommandError, match="DEBUG=True"):
        run_seed()
    assert get_user_model().objects.count() == 0
