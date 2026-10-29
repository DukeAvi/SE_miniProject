from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db.utils import NotSupportedError
from django.utils import timezone
from rest_framework.test import APIClient
from zoneinfo import ZoneInfo

from apps.audit.models import AuditEvent
from apps.donors.models import Donation, DonorProfile
from apps.donors.services import DonationRejected, record_completed_donation


pytestmark = pytest.mark.django_db
URL = "/api/v1/donations"
HISTORY_URL = "/api/v1/donors/me/donations"


def user(role, suffix):
    email = f"{role.lower()}{suffix}@example.test"
    return get_user_model().objects.create_user(
        username=email, email=email, password="Safe-Long-Password-532!",
        first_name="Synthetic", last_name="User", role=role,
    )


def profile(suffix=1, *, last_donation_date=None):
    donor = user("DONOR", suffix)
    return DonorProfile.objects.create(
        user=donor, birth_date=date(1990, 1, 1), weight_kg=Decimal("62.00"),
        blood_group="O+", last_donation_date=last_donation_date,
    )


def payload(donor, *, donation_date=None, **updates):
    value = {
        "donor_id": donor.user_id,
        "donation_date": (donation_date or date.today()).isoformat(),
        "blood_group": "O+",
        "component": "WHOLE_BLOOD",
        "quantity_units": 1,
        "status": "COMPLETED",
        "screening_weight_kg": "62.00",
    }
    value.update(updates)
    return value


def client_as(account):
    client = APIClient()
    client.force_authenticate(account)
    return client


def test_staff_records_completed_donation_and_updates_profile_and_audit_atomically():
    donor = profile()
    staff = user("STAFF", 2)

    response = client_as(staff).post(URL, payload(donor), format="json")

    assert response.status_code == 201
    assert response.json()["donor_id"] == donor.user_id
    assert Donation.objects.count() == 1
    donor.refresh_from_db()
    assert donor.last_donation_date == date.fromisoformat(response.json()["donation_date"])
    assert AuditEvent.objects.filter(action="DONATION_RECORDED", actor=staff).count() == 1


def test_recording_resolves_donor_id_as_the_account_id():
    user("RECIPIENT", 17)
    donor = profile(18)
    assert donor.pk != donor.user_id
    staff = user("STAFF", 19)

    response = client_as(staff).post(URL, payload(donor), format="json")

    assert response.status_code == 201
    assert response.json()["donor_id"] == donor.user_id


@pytest.mark.parametrize("role", ["DONOR", "RECIPIENT", "ADMIN"])
def test_non_staff_cannot_record_donations(role):
    donor = profile(3)
    response = client_as(user(role, 4)).post(URL, payload(donor), format="json")
    assert response.status_code == 403
    assert Donation.objects.count() == 0
    donor.refresh_from_db()
    assert donor.last_donation_date is None


def test_donation_service_rechecks_role_when_called_directly():
    donor = profile(32)
    recipient = user("RECIPIENT", 33)

    with pytest.raises(DonationRejected) as rejected:
        record_completed_donation(
            actor=recipient,
            donor_id=donor.user_id,
            donation_date=date.today(),
            blood_group="O+",
            component="WHOLE_BLOOD",
            quantity_units=1,
            screening_weight_kg=Decimal("62.00"),
        )

    assert rejected.value.code == "forbidden"
    assert Donation.objects.count() == 0
    donor.refresh_from_db()
    assert donor.last_donation_date is None


@pytest.mark.parametrize("changes", [
    {"component": "PLASMA"},
    {"blood_group": "A+"},
    {"screening_weight_kg": "49.99"},
    {"quantity_units": 0},
    {"unexpected": True},
])
def test_invalid_or_ineligible_record_is_rejected_without_changes(changes):
    donor = profile(5)
    response = client_as(user("STAFF", 6)).post(URL, payload(donor, **changes), format="json")
    assert response.status_code in (400, 422)
    assert Donation.objects.count() == 0
    donor.refresh_from_db()
    assert donor.last_donation_date is None
    assert not AuditEvent.objects.filter(action="DONATION_RECORDED").exists()


@pytest.mark.parametrize(
    "changes",
    [
        {"donor_id": "1 OR 1=1"},
        {"blood_group": "<script>alert(1)</script>"},
        {"component": "WHOLE_BLOOD'; DROP TABLE donors_donation; --"},
        {"screening_weight_kg": "999999999999999999999"},
        {"unexpected": "{{7*7}}"},
    ],
)
def test_injection_shaped_or_oversized_donation_input_is_rejected(changes):
    donor = profile(30)
    staff = user("STAFF", 31)

    response = client_as(staff).post(URL, payload(donor, **changes), format="json")

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "validation_error"
    assert Donation.objects.count() == 0
    donor.refresh_from_db()
    assert donor.last_donation_date is None
    assert not AuditEvent.objects.filter(action="DONATION_RECORDED").exists()


def test_donation_interval_rejects_day_55_and_accepts_day_56():
    donor = profile(7, last_donation_date=date.today() - timedelta(days=55))
    staff = user("STAFF", 8)
    too_soon = client_as(staff).post(URL, payload(donor), format="json")
    assert too_soon.status_code == 422
    donor.last_donation_date = date.today() - timedelta(days=56)
    donor.save(update_fields=("last_donation_date",))
    allowed = client_as(staff).post(URL, payload(donor), format="json")
    assert allowed.status_code == 201


def test_future_date_and_missing_donor_are_rejected():
    donor = profile(9)
    staff = user("STAFF", 10)
    blood_bank_today = timezone.now().astimezone(ZoneInfo(settings.BLOOD_BANK_TIME_ZONE)).date()
    future = client_as(staff).post(URL, payload(donor, donation_date=blood_bank_today + timedelta(days=1)), format="json")
    missing = client_as(staff).post(URL, {**payload(donor), "donor_id": donor.pk + 999}, format="json")
    assert future.status_code == 422
    assert missing.status_code == 404
    assert Donation.objects.count() == 0


def test_donor_history_is_owned_and_staff_cannot_view_it():
    owner = profile(11)
    staff = user("STAFF", 12)
    client = client_as(staff)
    assert client.post(URL, payload(owner), format="json").status_code == 201
    history = client_as(owner.user).get(HISTORY_URL)
    assert history.status_code == 200
    assert len(history.json()["results"]) == 1
    assert client_as(staff).get(HISTORY_URL).status_code == 403


def test_donor_history_never_returns_another_donors_records():
    owner = profile(34)
    other = profile(35)
    staff = user("STAFF", 36)
    assert client_as(staff).post(URL, payload(owner), format="json").status_code == 201

    owner_history = client_as(owner.user).get(HISTORY_URL)
    other_history = client_as(other.user).get(HISTORY_URL)

    assert owner_history.status_code == other_history.status_code == 200
    assert len(owner_history.json()["results"]) == 1
    assert other_history.json()["results"] == []


def test_donation_records_cannot_be_updated_or_deleted():
    donor = profile(13)
    response = client_as(user("STAFF", 14)).post(URL, payload(donor), format="json")
    donation = Donation.objects.get(pk=response.json()["id"])
    donation.quantity_units = 2
    with pytest.raises(ValidationError):
        donation.save()
    with pytest.raises(ValidationError):
        donation.delete()
    with pytest.raises(NotSupportedError):
        Donation.objects.filter(pk=donation.pk).update(quantity_units=2)
    with pytest.raises(NotSupportedError):
        Donation.objects.filter(pk=donation.pk).delete()


def test_audit_failure_rolls_back_donation_and_profile_update(monkeypatch):
    donor = profile(15)
    staff = user("STAFF", 16)

    def fail_audit(**kwargs):
        raise RuntimeError("audit unavailable")

    monkeypatch.setattr("apps.donors.services.record_event", fail_audit)
    with pytest.raises(RuntimeError, match="audit unavailable"):
        record_completed_donation(
            actor=staff, donor_id=donor.pk, donation_date=date.today(),
            blood_group="O+", component="WHOLE_BLOOD", quantity_units=1,
            screening_weight_kg=Decimal("62.00"),
        )

    assert Donation.objects.count() == 0
    donor.refresh_from_db()
    assert donor.last_donation_date is None


def test_recording_endpoint_requires_authentication():
    assert APIClient().post(URL, {}, format="json").status_code == 401
