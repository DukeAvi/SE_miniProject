import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import check_password
from rest_framework.test import APIClient


pytestmark = pytest.mark.django_db

REGISTER_URL = "/api/v1/auth/register"
PASSWORD = "Safe-Long-Password-532!"


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
    assert field in response.json()
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
    assert "email" in response.json()
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
    assert "phone" in response.json()
    assert get_user_model().objects.count() == 1


@pytest.mark.parametrize("missing", ["email", "first_name", "last_name", "phone", "password", "role"])
def test_missing_required_field_is_rejected_without_account(missing):
    data = payload()
    data.pop(missing)

    response = APIClient().post(REGISTER_URL, data, format="json")

    assert response.status_code == 400
    assert missing in response.json()
    assert get_user_model().objects.count() == 0
