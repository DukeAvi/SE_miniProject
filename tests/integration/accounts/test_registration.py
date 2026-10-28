from unittest.mock import patch
from uuid import UUID

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import check_password
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db

REGISTER_URL = "/api/v1/auth/register"
PASSWORD = "Safe-Long-Password-532!"


def email_with_total_length(length):
    local = "a" * 64
    remaining = length - len(local) - 1
    labels = []
    while remaining > 63:
        labels.append("d" * 63)
        remaining -= 64
    labels.append("e" * remaining)
    return f"{local}@{'.'.join(labels)}"


def payload(**overrides):
    data = {
        "email": "donor@example.test",
        "first_name": "Asha",
        "last_name": "Rao",
        "phone": "+1 202 555 0123",
        "password": PASSWORD,
        "role": "DONOR",
    }
    data.update(overrides)
    return data


@pytest.mark.parametrize("email_length", [170, 254])
def test_registers_long_supported_email_without_oversized_internal_username(email_length):
    email = email_with_total_length(email_length)
    response = APIClient().post(REGISTER_URL, payload(email=email), format="json")

    assert response.status_code == 201, response.content
    user = get_user_model().objects.get(email=email)
    assert len(user.username) <= 150
    assert user.username != email
    user.full_clean()


def test_email_one_character_over_supported_maximum_is_field_error_without_account():
    email = email_with_total_length(255)
    response = APIClient().post(REGISTER_URL, payload(email=email), format="json")

    assert response.status_code == 400
    assert "email" in response.json()["error"]["details"]
    assert get_user_model().objects.count() == 0


def test_internal_usernames_are_unique_and_duplicate_emails_remain_field_errors():
    client = APIClient()
    first = email_with_total_length(170)
    second = email_with_total_length(171).replace("a" * 64, "b" * 64, 1)
    assert client.post(REGISTER_URL, payload(email=first), format="json").status_code == 201
    assert client.post(
        REGISTER_URL,
        payload(email=second, phone="+442079460123"),
        format="json",
    ).status_code == 201
    usernames = list(get_user_model().objects.values_list("username", flat=True))
    assert len(usernames) == 2
    assert len(set(usernames)) == 2
    assert all(len(username) <= 150 for username in usernames)

    duplicate = client.post(
        REGISTER_URL,
        payload(email=first.upper(), phone="+442079460124"),
        format="json",
    )
    assert duplicate.status_code == 400
    assert "email" in duplicate.json()["error"]["details"]
    assert get_user_model().objects.count() == 2


def test_internal_username_collision_retries_without_exposing_an_error():
    collision = UUID(int=1).hex
    existing_email = "existing@example.test"
    get_user_model().objects.create_user(
        username=collision,
        email=existing_email,
        first_name="Existing",
        last_name="User",
        phone="+12025550124",
        role="DONOR",
        password=PASSWORD,
    )
    with patch(
        "apps.accounts.services.uuid4",
        side_effect=[UUID(int=1), UUID(int=2)],
    ):
        response = APIClient().post(REGISTER_URL, payload(), format="json")

    assert response.status_code == 201
    registered = get_user_model().objects.get(email="donor@example.test")
    assert registered.username == UUID(int=2).hex
    assert get_user_model().objects.count() == 2


def test_registers_donor_with_argon2_hash_and_public_response():
    response = APIClient().post(REGISTER_URL, payload(), format="json")

    assert response.status_code == 201
    assert response.json() == {
        "id": response.json()["id"],
        "email": "donor@example.test",
        "first_name": "Asha",
        "last_name": "Rao",
        "phone": "+12025550123",
        "role": "DONOR",
    }
    user = get_user_model().objects.get(email="donor@example.test")
    assert user.check_password(PASSWORD)
    assert user.password.startswith("argon2$")
    assert check_password(PASSWORD, user.password)
    assert not user.is_staff
    assert not user.is_superuser
    assert PASSWORD not in response.content.decode()


def test_registers_recipient_role():
    response = APIClient().post(
        REGISTER_URL,
        payload(email="recipient@example.test", role="RECIPIENT"),
        format="json",
    )

    assert response.status_code == 201
    assert response.json()["role"] == "RECIPIENT"


@pytest.mark.parametrize(
    ("overrides", "field"),
    [
        ({"email": "not-an-email"}, "email"),
        ({"phone": "123"}, "phone"),
        ({"first_name": ""}, "first_name"),
        ({"password": "password"}, "password"),
        ({"role": "ADMIN"}, "role"),
        ({"role": "STAFF"}, "role"),
    ],
)
def test_rejects_invalid_or_privileged_registration(overrides, field):
    response = APIClient().post(REGISTER_URL, payload(**overrides), format="json")

    assert response.status_code == 400
    assert field in response.json()["error"]["details"]
    assert get_user_model().objects.count() == 0


def test_duplicate_email_is_case_insensitive_and_has_field_error():
    client = APIClient()
    assert client.post(REGISTER_URL, payload(), format="json").status_code == 201

    response = client.post(
        REGISTER_URL,
        payload(email="DONOR@EXAMPLE.TEST", phone="+442079460123"),
        format="json",
    )

    assert response.status_code == 400
    assert "email" in response.json()["error"]["details"]
    assert get_user_model().objects.count() == 1


def test_duplicate_phone_is_normalized_and_has_field_error():
    client = APIClient()
    assert client.post(REGISTER_URL, payload(), format="json").status_code == 201

    response = client.post(
        REGISTER_URL,
        payload(email="other@example.test", phone="+1-202-555-0123"),
        format="json",
    )

    assert response.status_code == 400
    assert "phone" in response.json()["error"]["details"]
    assert get_user_model().objects.count() == 1


@pytest.mark.parametrize("missing", ["email", "first_name", "last_name", "phone", "password", "role"])
def test_missing_required_field_is_rejected_without_account(missing):
    data = payload()
    data.pop(missing)

    response = APIClient().post(REGISTER_URL, data, format="json")

    assert response.status_code == 400
    assert missing in response.json()["error"]["details"]
    assert get_user_model().objects.count() == 0


@pytest.mark.parametrize(
    "overrides",
    [
        {"unexpected": "value"},
        {"first_name": ["not", "text"]},
        {"role": "ADMIN"},
        {"email": "x@example.test' OR 1=1 --"},
        {"first_name": "x" * 151},
    ],
)
def test_rejects_unknown_typed_injection_and_oversized_fields(overrides):
    response = APIClient().post(REGISTER_URL, payload(**overrides), format="json")

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "validation_error"
    assert response.json()["error"]["correlation_id"]
    assert get_user_model().objects.count() == 0


def test_registration_response_has_security_headers_and_template_autoescapes():
    from django.template import Context, Template

    response = APIClient().post(REGISTER_URL, payload(), format="json")

    assert response["X-Content-Type-Options"] == "nosniff"
    assert "default-src 'self'" in response["Content-Security-Policy"]
    assert "<script>" not in Template("{{ value }}").render(
        Context({"value": "<script>alert(1)</script>"})
    )
