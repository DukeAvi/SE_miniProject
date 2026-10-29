import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from rest_framework.test import APIClient

from apps.accounts.models import AccountRole
from apps.accounts.services import update_profile
from apps.audit.models import AuditEvent


pytestmark = pytest.mark.django_db

PROFILE_URL = "/api/v1/users/me"
PASSWORD = "Safe-Long-Password-532!"


def make_user(role, index):
    email = f"{role.lower()}{index}@example.test"
    return get_user_model().objects.create_user(
        username=email,
        email=email,
        password=PASSWORD,
        first_name="Test",
        last_name=role.title(),
        phone=f"+1202555{index:04d}",
        role=role,
    )


@pytest.mark.parametrize("role", AccountRole.values)
def test_each_role_reads_and_updates_only_its_own_permitted_profile(role):
    user = make_user(role, AccountRole.values.index(role) + 1)
    client = APIClient()
    client.force_authenticate(user)

    initial = client.get(PROFILE_URL)
    updated = client.patch(
        PROFILE_URL,
        {"first_name": "Updated", "phone": "+12025550999"},
        format="json",
    )

    assert initial.status_code == 200
    assert initial.json()["id"] == user.pk
    assert initial.json()["email"] == user.email
    assert initial.json()["role"] == role
    assert updated.status_code == 200
    assert updated.json()["first_name"] == "Updated"
    assert updated.json()["phone"] == "+12025550999"
    user.refresh_from_db()
    assert user.first_name == "Updated"


@pytest.mark.parametrize(
    "protected_changes",
    [
        {"role": "ADMIN"},
        {"is_active": False},
        {"email": "attacker@example.test"},
        {"password": "Compromised-Password-1!"},
        {"date_of_birth": "2000-01-01"},
        {"unknown": "value"},
    ],
)
def test_profile_rejects_protected_and_unknown_fields_without_partial_save(protected_changes):
    user = make_user("DONOR", 10)
    client = APIClient()
    client.force_authenticate(user)

    response = client.patch(
        PROFILE_URL,
        {"first_name": "Should Not Persist", **protected_changes},
        format="json",
    )

    assert response.status_code == 400
    user.refresh_from_db()
    assert user.first_name == "Test"
    assert user.role == "DONOR"
    assert user.is_active is True


@pytest.mark.parametrize("phone", ["123", "+12025550021", "x" * 17])
def test_invalid_or_duplicate_phone_is_rejected_without_partial_save(phone):
    user = make_user("RECIPIENT", 20)
    make_user("DONOR", 21)
    client = APIClient()
    client.force_authenticate(user)

    response = client.patch(
        PROFILE_URL,
        {"first_name": "Should Not Persist", "phone": phone},
        format="json",
    )

    assert response.status_code == 400
    assert "phone" in response.json()["error"]["details"]
    user.refresh_from_db()
    assert user.first_name == "Test"


def test_donor_profile_update_is_audited_and_service_rechecks_fields():
    donor = make_user("DONOR", 30)
    client = APIClient()
    client.force_authenticate(donor)
    response = client.patch(PROFILE_URL, {"last_name": "Changed"}, format="json")

    assert response.status_code == 200
    assert AuditEvent.objects.filter(action="DONOR_UPDATED", actor=donor).count() == 1
    with pytest.raises(PermissionDenied):
        update_profile(user=donor, changes={"role": "ADMIN"})


def test_profile_requires_authentication():
    response = APIClient().get(PROFILE_URL)
    assert response.status_code == 401


def test_profile_requests_cannot_read_or_update_another_accounts_profile():
    owner = make_user("DONOR", 50)
    other = make_user("RECIPIENT", 51)
    client = APIClient()
    client.force_authenticate(owner)

    current_profile = client.get(f"{PROFILE_URL}?user_id={other.pk}")
    foreign_profile_route = client.get(f"/api/v1/users/{other.pk}")
    foreign_update = client.patch(
        PROFILE_URL,
        {"user_id": other.pk, "first_name": "Unauthorized"},
        format="json",
    )

    assert current_profile.status_code == 200
    assert current_profile.json()["id"] == owner.pk
    assert current_profile.json()["email"] == owner.email
    assert other.email not in current_profile.content.decode()
    assert foreign_profile_route.status_code == 404
    assert foreign_update.status_code == 400
    owner.refresh_from_db()
    other.refresh_from_db()
    assert owner.first_name == "Test"
    assert other.first_name == "Test"


def test_profile_patch_requires_csrf_for_session_authenticated_user():
    user = make_user("DONOR", 40)
    client = APIClient(enforce_csrf_checks=True)
    csrf_token = client.get("/api/v1/auth/csrf", secure=True).json()["csrfToken"]
    login = client.post(
        "/api/v1/auth/login",
        {"email": user.email, "password": PASSWORD},
        format="json",
        secure=True,
        HTTP_REFERER="https://testserver/",
        HTTP_X_CSRFTOKEN=csrf_token,
    )
    assert login.status_code == 200
    csrf_token = client.get("/api/v1/auth/csrf", secure=True).json()["csrfToken"]

    rejected = client.patch(
        PROFILE_URL,
        {"first_name": "Blocked"},
        format="json",
        secure=True,
        HTTP_REFERER="https://testserver/",
    )
    accepted = client.patch(
        PROFILE_URL,
        {"first_name": "Protected"},
        format="json",
        secure=True,
        HTTP_REFERER="https://testserver/",
        HTTP_X_CSRFTOKEN=csrf_token,
    )

    assert rejected.status_code == 403
    assert accepted.status_code == 200
    user.refresh_from_db()
    assert user.first_name == "Protected"
