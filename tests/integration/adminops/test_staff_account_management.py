from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.contrib.sessions.models import Session
from rest_framework.test import APIClient

from apps.adminops.services import (
    ManagedUserRejected,
    create_managed_user,
    update_managed_user,
)
from apps.audit.models import AuditEvent


pytestmark = pytest.mark.django_db

USERS_URL = "/api/v1/admin/users"
PASSWORD = "Synthetic-Test-Password-532!"


def make_user(role, index=1, *, is_active=True):
    return get_user_model().objects.create_user(
        username=f"{role.lower()}-{index}@example.test",
        email=f"{role.lower()}-{index}@example.test",
        phone=f"+1202555{index:04d}",
        first_name="Synthetic",
        last_name=role.title(),
        role=role,
        is_active=is_active,
        password=PASSWORD,
    )


def create_payload(**overrides):
    data = {
        "email": "managed.staff@example.test",
        "first_name": "Managed",
        "last_name": "Staff",
        "phone": "+1 202 555 0199",
        "password": PASSWORD,
        "role": "STAFF",
    }
    data.update(overrides)
    return data


def session_client(user):
    client = APIClient(enforce_csrf_checks=True)
    token = client.get("/api/v1/auth/csrf", secure=True).json()["csrfToken"]
    login = client.post(
        "/api/v1/auth/login",
        {"email": user.email, "password": PASSWORD},
        format="json",
        secure=True,
        HTTP_REFERER="https://testserver/",
        HTTP_X_CSRFTOKEN=token,
    )
    assert login.status_code == 200
    return client


def csrf_session_client(user):
    client = APIClient(enforce_csrf_checks=True)
    token = client.get("/api/v1/auth/csrf", secure=True).json()["csrfToken"]
    login = client.post(
        "/api/v1/auth/login",
        {"email": user.email, "password": PASSWORD},
        format="json",
        secure=True,
        HTTP_REFERER="https://testserver/",
        HTTP_X_CSRFTOKEN=token,
    )
    assert login.status_code == 200
    token = client.get("/api/v1/auth/csrf", secure=True).json()["csrfToken"]
    return client, token


@pytest.mark.parametrize("role", ["STAFF", "ADMIN"])
def test_admin_creates_managed_account_with_audit_metadata(role):
    admin = make_user("ADMIN")
    client = APIClient()
    client.force_authenticate(admin)

    response = client.post(USERS_URL, create_payload(role=role), format="json")

    assert response.status_code == 201, response.content
    assert set(response.json()) == {
        "id", "email", "first_name", "last_name", "phone", "role",
    }
    user = get_user_model().objects.get(pk=response.json()["id"])
    assert user.check_password(PASSWORD)
    assert user.password.startswith("argon2$")
    assert user.username != user.email
    assert not user.is_staff
    assert not user.is_superuser
    assert PASSWORD not in response.content.decode()
    event = AuditEvent.objects.get(action="USER_CREATED")
    assert event.actor == admin
    assert event.actor_role == "ADMIN"
    assert event.entity_type == "USER"
    assert event.entity_id == str(user.pk)
    assert event.outcome == "SUCCESS"


@pytest.mark.parametrize("role", ["DONOR", "RECIPIENT", "STAFF"])
def test_non_admin_roles_cannot_create_or_list_managed_accounts(role):
    actor = make_user(role)
    client = APIClient()
    client.force_authenticate(actor)

    created = client.post(USERS_URL, create_payload(), format="json")
    listed = client.get(USERS_URL)

    assert created.status_code == listed.status_code == 403
    assert not get_user_model().objects.filter(email="managed.staff@example.test").exists()


def test_managed_account_changes_require_csrf_for_session_authentication():
    admin = make_user("ADMIN")
    client, token = csrf_session_client(admin)

    rejected = client.post(
        USERS_URL,
        create_payload(),
        format="json",
        secure=True,
        HTTP_REFERER="https://testserver/",
    )
    accepted = client.post(
        USERS_URL,
        create_payload(),
        format="json",
        secure=True,
        HTTP_REFERER="https://testserver/",
        HTTP_X_CSRFTOKEN=token,
    )

    assert rejected.status_code == 403
    assert rejected.json()["error"]["code"] == "csrf_failed"
    assert accepted.status_code == 201


@pytest.mark.parametrize(
    ("overrides", "field"),
    [
        ({"email": "not-an-email"}, "email"),
        ({"phone": "123"}, "phone"),
        ({"password": "password"}, "password"),
        ({"role": "DONOR"}, "role"),
        ({"first_name": ["not", "text"]}, "first_name"),
        ({"unexpected": "value"}, "non_field_errors"),
    ],
)
def test_invalid_managed_account_creation_saves_nothing(overrides, field):
    admin = make_user("ADMIN")
    client = APIClient()
    client.force_authenticate(admin)

    response = client.post(
        USERS_URL,
        create_payload(**overrides),
        format="json",
    )

    assert response.status_code == 400
    assert field in response.json()["error"]["details"]
    assert not get_user_model().objects.filter(email="managed.staff@example.test").exists()
    assert not AuditEvent.objects.filter(action="USER_CREATED").exists()


def test_admin_list_is_paginated_and_excludes_public_accounts():
    admin = make_user("ADMIN")
    staff = make_user("STAFF", 2)
    make_user("DONOR", 3)
    make_user("RECIPIENT", 4)
    client = APIClient()
    client.force_authenticate(admin)

    response = client.get(f"{USERS_URL}?page=1&page_size=1")

    assert response.status_code == 200
    assert response.json()["count"] == 2
    assert response.json()["page_size"] == 1
    returned_ids = {response.json()["results"][0]["id"]}
    assert returned_ids <= {admin.pk, staff.pk}


def test_admin_user_list_caps_page_size_at_100():
    admin = make_user("ADMIN", 501)
    client = APIClient()
    client.force_authenticate(admin)

    response = client.get(f"{USERS_URL}?page=1&page_size=101")

    assert response.status_code == 200
    assert response.json()["page_size"] == 100
    assert len(response.json()["results"]) <= 100


def test_disabling_account_revokes_every_active_session_and_is_audited():
    admin = make_user("ADMIN")
    staff = make_user("STAFF", 2)
    first = session_client(staff)
    second = session_client(staff)
    assert first.cookies["sessionid"].value != second.cookies["sessionid"].value
    assert Session.objects.count() == 2
    client = APIClient()
    client.force_authenticate(admin)

    response = client.patch(
        f"{USERS_URL}/{staff.pk}",
        {"is_active": False},
        format="json",
    )

    assert response.status_code == 200
    staff.refresh_from_db()
    assert not staff.is_active
    assert Session.objects.count() == 0
    assert first.get("/api/v1/users/me").status_code == 401
    event = AuditEvent.objects.get(action="USER_DISABLED")
    assert event.actor == admin
    assert event.entity_id == str(staff.pk)
    assert event.outcome == "SUCCESS"


def test_role_change_applies_to_an_existing_session_and_is_audited():
    admin = make_user("ADMIN")
    staff = make_user("STAFF", 2)
    staff_client = session_client(staff)
    client = APIClient()
    client.force_authenticate(admin)

    response = client.patch(
        f"{USERS_URL}/{staff.pk}",
        {"role": "ADMIN"},
        format="json",
    )

    assert response.status_code == 200
    assert staff_client.get(USERS_URL).status_code == 200
    event = AuditEvent.objects.get(action="ROLE_CHANGED")
    assert event.actor == admin
    assert event.entity_id == str(staff.pk)


@pytest.mark.parametrize(
    ("payload", "field"),
    [
        ({}, "non_field_errors"),
        ({"role": "DONOR"}, "role"),
        ({"is_active": "false"}, "is_active"),
        ({"unexpected": True}, "non_field_errors"),
    ],
)
def test_invalid_managed_updates_change_nothing(payload, field):
    admin = make_user("ADMIN")
    staff = make_user("STAFF", 2)
    client = APIClient()
    client.force_authenticate(admin)

    response = client.patch(f"{USERS_URL}/{staff.pk}", payload, format="json")

    assert response.status_code == 400
    assert field in response.json()["error"]["details"]
    staff.refresh_from_db()
    assert staff.role == "STAFF"
    assert staff.is_active


def test_public_account_cannot_be_changed_through_managed_endpoint():
    admin = make_user("ADMIN")
    donor = make_user("DONOR", 2)
    client = APIClient()
    client.force_authenticate(admin)

    response = client.patch(
        f"{USERS_URL}/{donor.pk}",
        {"role": "STAFF"},
        format="json",
    )

    assert response.status_code == 404
    donor.refresh_from_db()
    assert donor.role == "DONOR"


def test_duplicate_email_and_phone_are_field_errors():
    admin = make_user("ADMIN")
    existing = make_user("STAFF", 2)
    client = APIClient()
    client.force_authenticate(admin)

    duplicate_email = client.post(
        USERS_URL,
        create_payload(email=existing.email.upper()),
        format="json",
    )
    duplicate_phone = client.post(
        USERS_URL,
        create_payload(email="other@example.test", phone=existing.phone),
        format="json",
    )

    assert duplicate_email.status_code == duplicate_phone.status_code == 400
    assert "email" in duplicate_email.json()["error"]["details"]
    assert "phone" in duplicate_phone.json()["error"]["details"]


def test_service_rechecks_admin_role_and_active_state():
    inactive_admin = make_user("ADMIN", is_active=False)

    with pytest.raises(ManagedUserRejected) as rejected:
        create_managed_user(actor=inactive_admin, **create_payload())

    assert rejected.value.code == "forbidden"
    assert not get_user_model().objects.filter(email="managed.staff@example.test").exists()


def test_audit_failure_rolls_back_create_and_update():
    admin = make_user("ADMIN")
    staff = make_user("STAFF", 2)
    with patch("apps.adminops.services.record_event", side_effect=RuntimeError("audit unavailable")):
        with pytest.raises(RuntimeError):
            create_managed_user(actor=admin, **create_payload())
        with pytest.raises(RuntimeError):
            update_managed_user(
                actor=admin,
                user_id=staff.pk,
                changes={"is_active": False},
            )

    assert not get_user_model().objects.filter(email="managed.staff@example.test").exists()
    staff.refresh_from_db()
    assert staff.is_active
