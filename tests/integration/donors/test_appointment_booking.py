from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier
from zoneinfo import ZoneInfo

import pytest
from django.contrib.auth import get_user_model
from django.db import close_old_connections, connection
from django.utils import timezone
from rest_framework.test import APIClient

from apps.audit.models import AuditEvent
from apps.donors.models import Appointment, DonationSlot, DonorProfile


pytestmark = pytest.mark.django_db
SLOTS_URL = "/api/v1/donation-slots"
APPOINTMENTS_URL = "/api/v1/donors/me/appointments"


def make_user(role, suffix):
    email = f"appointments-{role.lower()}-{suffix}@example.test"
    return get_user_model().objects.create_user(
        username=email, email=email, password="Safe-Long-Password-532!",
        first_name="Synthetic", last_name="User", role=role,
    )


def make_donor(suffix, *, last_donation_date=None):
    user = make_user("DONOR", suffix)
    return DonorProfile.objects.create(
        user=user, birth_date=timezone.localdate() - timedelta(days=30 * 365),
        weight_kg="62.00", blood_group="O+", last_donation_date=last_donation_date,
    )


def make_slot(*, capacity=10, starts_at=None):
    return DonationSlot.objects.create(
        starts_at=starts_at or timezone.now() + timedelta(days=3), capacity=capacity,
    )


def client_for(user):
    client = APIClient()
    client.force_authenticate(user)
    return client


def test_donor_lists_local_date_slots_with_live_capacity():
    donor = make_donor(1)
    slot = make_slot(capacity=3)
    response = client_for(donor.user).get(
        SLOTS_URL,
        {"date": slot.starts_at.astimezone(ZoneInfo("Asia/Kolkata")).date().isoformat()},
    )
    assert response.status_code == 200
    listed = next(item for item in response.json()["results"] if item["slot_id"] == str(slot.pk))
    assert listed["capacity"] == 3
    assert listed["available_capacity"] == 3


def test_staff_can_list_slots_but_cannot_book_for_a_donor():
    slot = make_slot()
    staff = make_user("STAFF", 2)
    client = client_for(staff)
    date_value = slot.starts_at.astimezone(ZoneInfo("Asia/Kolkata")).date().isoformat()
    listed = client.get(SLOTS_URL, {"date": date_value})
    booking = client.post(APPOINTMENTS_URL, {"slot_id": str(slot.pk)}, format="json")
    assert listed.status_code == 200
    assert booking.status_code == 403
    assert Appointment.objects.count() == 0


def test_eligible_donor_books_and_sees_appointment_and_audit_event():
    donor = make_donor(3)
    slot = make_slot()
    response = client_for(donor.user).post(APPOINTMENTS_URL, {"slot_id": str(slot.pk)}, format="json")
    assert response.status_code == 201
    assert response.json()["status"] == Appointment.Status.BOOKED
    assert response.json()["slot_id"] == str(slot.pk)
    history = client_for(donor.user).get(APPOINTMENTS_URL)
    assert history.status_code == 200
    assert history.json()["results"][0]["appointment_id"] == response.json()["appointment_id"]
    assert AuditEvent.objects.filter(action="APPOINTMENT_BOOKED", actor=donor.user).count() == 1


def test_ineligible_donor_does_not_consume_capacity():
    donor = make_donor(4, last_donation_date=timezone.localdate() - timedelta(days=52))
    slot = make_slot(capacity=1)
    response = client_for(donor.user).post(APPOINTMENTS_URL, {"slot_id": str(slot.pk)}, format="json")
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "donor_ineligible"
    assert Appointment.objects.count() == 0

    eligible = make_donor(5)
    booked = client_for(eligible.user).post(APPOINTMENTS_URL, {"slot_id": str(slot.pk)}, format="json")
    assert booked.status_code == 201


def test_donor_is_eligible_at_exact_56_day_boundary():
    slot = make_slot()
    slot_local_date = slot.starts_at.astimezone(ZoneInfo("Asia/Kolkata")).date()
    donor = make_donor(22, last_donation_date=slot_local_date - timedelta(days=56))
    response = client_for(donor.user).post(APPOINTMENTS_URL, {"slot_id": str(slot.pk)}, format="json")
    assert response.status_code == 201


def test_full_slot_and_duplicate_booking_return_conflicts():
    first = make_donor(6)
    second = make_donor(7)
    slot = make_slot(capacity=1)
    client = client_for(first.user)
    assert client.post(APPOINTMENTS_URL, {"slot_id": str(slot.pk)}, format="json").status_code == 201
    duplicate = client.post(APPOINTMENTS_URL, {"slot_id": str(slot.pk)}, format="json")
    full = client_for(second.user).post(APPOINTMENTS_URL, {"slot_id": str(slot.pk)}, format="json")
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "duplicate_appointment"
    assert full.status_code == 409
    assert full.json()["error"]["code"] == "slot_full"
    assert Appointment.objects.filter(slot=slot, status=Appointment.Status.BOOKED).count() == 1


def test_missing_slot_and_donor_profile_return_not_found():
    donor = make_donor(8)
    missing = client_for(donor.user).post(APPOINTMENTS_URL, {"slot_id": "00000000-0000-4000-8000-000000000099"}, format="json")
    unprofiled = make_user("DONOR", 9)
    slot = make_slot()
    no_profile = client_for(unprofiled).post(APPOINTMENTS_URL, {"slot_id": str(slot.pk)}, format="json")
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "slot_not_found"
    assert no_profile.status_code == 404


def test_only_owner_can_cancel_and_cancelled_booking_releases_capacity():
    owner = make_donor(10)
    other = make_donor(11)
    slot = make_slot(capacity=1)
    created = client_for(owner.user).post(APPOINTMENTS_URL, {"slot_id": str(slot.pk)}, format="json")
    appointment_id = created.json()["appointment_id"]
    cancel_url = f"{APPOINTMENTS_URL}/{appointment_id}/cancel"

    foreign_cancel = client_for(other.user).post(cancel_url, {}, format="json")
    malformed_cancel = client_for(owner.user).post(f"{APPOINTMENTS_URL}/not-a-uuid/cancel", {}, format="json")
    owner_cancel = client_for(owner.user).post(cancel_url, {}, format="json")
    repeated_cancel = client_for(owner.user).post(cancel_url, {}, format="json")
    replacement = client_for(other.user).post(APPOINTMENTS_URL, {"slot_id": str(slot.pk)}, format="json")

    assert foreign_cancel.status_code == 404
    assert AuditEvent.objects.filter(action="ACCESS_DENIED", actor=other.user).count() == 1
    assert malformed_cancel.status_code == 404
    assert owner_cancel.status_code == 200
    assert owner_cancel.json()["status"] == Appointment.Status.CANCELLED
    assert repeated_cancel.status_code == 409
    assert replacement.status_code == 201


def test_cancelled_appointments_remain_in_owner_history():
    donor = make_donor(12)
    slot = make_slot()
    created = client_for(donor.user).post(APPOINTMENTS_URL, {"slot_id": str(slot.pk)}, format="json")
    client_for(donor.user).post(f"{APPOINTMENTS_URL}/{created.json()['appointment_id']}/cancel", {}, format="json")
    history = client_for(donor.user).get(APPOINTMENTS_URL)
    assert history.status_code == 200
    assert history.json()["results"][0]["status"] == Appointment.Status.CANCELLED


@pytest.mark.skipif(connection.vendor != "postgresql", reason="PostgreSQL row-lock behavior is not available on SQLite")
@pytest.mark.django_db(transaction=True)
def test_concurrent_bookings_cannot_exceed_slot_capacity():
    slot = make_slot(capacity=1)
    donors = [make_donor(20), make_donor(21)]
    barrier = Barrier(2)

    def attempt(donor_id):
        close_old_connections()
        user = get_user_model().objects.get(pk=donor_id)
        barrier.wait()
        response = client_for(user).post(APPOINTMENTS_URL, {"slot_id": str(slot.pk)}, format="json")
        close_old_connections()
        return response.status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(attempt, [donor.user_id for donor in donors]))
    assert sorted(results) == [201, 409]
    assert Appointment.objects.filter(slot=slot, status=Appointment.Status.BOOKED).count() == 1
