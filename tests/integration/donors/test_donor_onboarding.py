from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient
from zoneinfo import ZoneInfo

from apps.audit.models import AuditEvent
from apps.donors.models import Appointment, DonationSlot, DonorProfile
from apps.donors.onboarding import DonorOnboardingRejected, find_donors


pytestmark = pytest.mark.django_db

LOOKUP_URL = "/api/v1/donors/staff/donors"
PROFILE_URL = "/api/v1/donors/staff/donor-profiles"
REGISTER_URL = "/api/v1/auth/register"
APPOINTMENTS_URL = "/api/v1/donors/me/appointments"
DONATIONS_URL = "/api/v1/donors/me/donations"
PASSWORD = "Safe-Long-Password-532!"


def make_user(role, suffix, *, active=True):
    email = f"onboarding-{role.lower()}-{suffix}@example.test"
    return get_user_model().objects.create_user(
        username=email,
        email=email,
        password=PASSWORD,
        first_name="Synthetic",
        last_name=f"Person{suffix}",
        role=role,
        is_active=active,
    )


def client_for(user):
    client = APIClient()
    client.force_authenticate(user)
    return client


def profile_payload(donor_id, **changes):
    value = {
        "donor_id": donor_id,
        "birth_date": (date.today() - timedelta(days=30 * 365)).isoformat(),
        "weight_kg": "62.00",
        "blood_group": "O+",
    }
    value.update(changes)
    return value


def register_donor(email="fresh-donor@example.test", phone="+12025550133"):
    return APIClient().post(
        REGISTER_URL,
        {
            "email": email,
            "first_name": "Fresh",
            "last_name": "Donor",
            "phone": phone,
            "password": PASSWORD,
            "role": "DONOR",
        },
        format="json",
    )


def test_staff_can_find_active_donors_with_minimal_account_information():
    donor = make_user("DONOR", 1)
    inactive = make_user("DONOR", 2, active=False)
    make_user("RECIPIENT", 3)
    staff = make_user("STAFF", 4)

    response = client_for(staff).get(LOOKUP_URL, {"q": "person1"})

    assert response.status_code == 200
    assert response.json()["results"] == [
        {
            "id": donor.pk,
            "email": donor.email,
            "first_name": donor.first_name,
            "last_name": donor.last_name,
            "has_donor_profile": False,
        }
    ]
    assert inactive.email not in str(response.json())
    assert "phone" not in response.json()["results"][0]
    assert "birth_date" not in response.json()["results"][0]


@pytest.mark.parametrize("role", ["DONOR", "RECIPIENT", "ADMIN"])
def test_non_staff_cannot_search_or_create_donor_profiles(role):
    donor = make_user("DONOR", 10)
    client = client_for(make_user(role, 11))

    assert client.get(LOOKUP_URL, {"q": "fresh"}).status_code == 403
    assert client.post(PROFILE_URL, profile_payload(donor.pk), format="json").status_code == 403
    assert DonorProfile.objects.count() == 0


def test_lookup_requires_a_bounded_search_query():
    staff = client_for(make_user("STAFF", 12))

    assert staff.get(LOOKUP_URL).status_code == 400
    assert staff.get(LOOKUP_URL, {"q": "a"}).status_code == 400
    assert staff.get(LOOKUP_URL, {"q": "fresh", "page": "1"}).status_code == 400


@pytest.mark.parametrize("role,active", [("DONOR", True), ("RECIPIENT", True), ("ADMIN", True), ("STAFF", False)])
def test_lookup_service_rejects_unauthorized_actors_without_relying_on_view(role, active):
    actor = make_user(role, 120, active=active)
    with pytest.raises(DonorOnboardingRejected) as error:
        list(find_donors(actor=actor, query="person"))
    assert error.value.status_code == 403


def test_staff_creates_verified_profile_and_audits_without_exposing_medical_fields():
    donor = make_user("DONOR", 13)
    staff = make_user("STAFF", 14)

    response = client_for(staff).post(PROFILE_URL, profile_payload(donor.pk), format="json")

    assert response.status_code == 201
    assert response.json() == {"donor_id": donor.pk, "profile_status": "VERIFIED"}
    created = DonorProfile.objects.get(user=donor)
    assert created.birth_date == date.fromisoformat(profile_payload(donor.pk)["birth_date"])
    assert created.weight_kg == Decimal("62.00")
    assert created.blood_group == "O+"
    assert AuditEvent.objects.filter(
        action="DONOR_PROFILE_CREATED", actor=staff, entity_id=str(donor.pk)
    ).count() == 1


def test_new_donor_can_reach_appointments_and_history_after_staff_profile_completion():
    registered = register_donor()
    assert registered.status_code == 201
    donor_id = registered.json()["id"]
    donor = get_user_model().objects.get(pk=donor_id)
    donor_client = client_for(donor)
    staff_client = client_for(make_user("STAFF", 15))

    missing_profile = donor_client.get(APPOINTMENTS_URL)
    assert missing_profile.status_code == 404
    assert missing_profile.json()["error"]["code"] == "donor_profile_not_found"
    missing_history = donor_client.get(DONATIONS_URL)
    assert missing_history.status_code == 404
    assert missing_history.json()["error"]["code"] == "donor_profile_not_found"

    lookup = staff_client.get(LOOKUP_URL, {"q": donor.email})
    assert lookup.status_code == 200
    assert lookup.json()["results"][0]["has_donor_profile"] is False
    completed = staff_client.post(PROFILE_URL, profile_payload(donor_id), format="json")
    assert completed.status_code == 201

    appointments = donor_client.get(APPOINTMENTS_URL)
    donations = donor_client.get(DONATIONS_URL)
    assert appointments.status_code == 200
    assert appointments.json()["results"] == []
    assert donations.status_code == 200
    assert donations.json()["results"] == []

    slot = DonationSlot.objects.create(starts_at=timezone.now() + timedelta(days=3))
    booked = donor_client.post(APPOINTMENTS_URL, {"slot_id": str(slot.pk)}, format="json")
    assert booked.status_code == 201
    assert booked.json()["status"] == Appointment.Status.BOOKED
    assert donor_client.get(APPOINTMENTS_URL).json()["results"][0]["appointment_id"] == booked.json()["appointment_id"]


def test_profile_create_rejects_unknown_inactive_and_non_donor_accounts():
    staff = client_for(make_user("STAFF", 16))
    inactive = make_user("DONOR", 17, active=False)
    recipient = make_user("RECIPIENT", 18)

    for donor_id in (inactive.pk, recipient.pk, 999999):
        response = staff.post(PROFILE_URL, profile_payload(donor_id), format="json")
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "donor_not_found"
    assert DonorProfile.objects.count() == 0


def test_profile_create_rejects_future_birth_date_invalid_group_and_unexpected_fields():
    staff = client_for(make_user("STAFF", 19))
    future = timezone.now().astimezone(ZoneInfo(settings.BLOOD_BANK_TIME_ZONE)).date() + timedelta(days=1)
    donor = make_user("DONOR", 20)

    cases = [
        ({"birth_date": future.isoformat()}, "birth_date"),
        ({"blood_group": "X+"}, "blood_group"),
        ({"weight_kg": "1000000"}, "weight_kg"),
        ({"unexpected": "value"}, "non_field_errors"),
    ]
    for changes, field in cases:
        response = staff.post(PROFILE_URL, profile_payload(donor.pk, **changes), format="json")
        assert response.status_code == 400
        assert field in response.json()["error"]["details"]
    assert DonorProfile.objects.count() == 0


def test_profile_is_create_once_and_duplicate_submission_does_not_change_it():
    donor = make_user("DONOR", 21)
    staff = client_for(make_user("STAFF", 22))
    first = staff.post(PROFILE_URL, profile_payload(donor.pk), format="json")
    second = staff.post(
        PROFILE_URL,
        profile_payload(donor.pk, blood_group="A+", weight_kg="70.00"),
        format="json",
    )

    assert first.status_code == 201
    assert second.status_code == 409
    profile = DonorProfile.objects.get(user=donor)
    assert profile.blood_group == "O+"
    assert profile.weight_kg == Decimal("62.00")
    assert AuditEvent.objects.filter(action="DONOR_PROFILE_CREATED").count() == 1


def test_profile_and_audit_are_atomic(monkeypatch):
    donor = make_user("DONOR", 23)
    staff = make_user("STAFF", 24)

    def fail_audit(**kwargs):
        raise RuntimeError("audit unavailable")

    monkeypatch.setattr("apps.donors.onboarding.record_event", fail_audit)
    with pytest.raises(RuntimeError, match="audit unavailable"):
        from apps.donors.onboarding import create_donor_profile

        create_donor_profile(
            actor=staff,
            donor_id=donor.pk,
            birth_date=date(1990, 1, 1),
            weight_kg=Decimal("62.00"),
            blood_group="O+",
        )

    assert not DonorProfile.objects.filter(user=donor).exists()
