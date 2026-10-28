import logging

import pytest
from rest_framework.test import APIClient


pytestmark = pytest.mark.django_db


def test_registration_and_authentication_paths_do_not_log_credentials(caplog):
    caplog.set_level(logging.INFO)
    client = APIClient(enforce_csrf_checks=True)
    csrf = client.get("/api/v1/auth/csrf", secure=True).json()["csrfToken"]
    email = "private-contact@example.test"
    phone = "+442079460123"
    password = "Unique-Private-Password-772!"

    registration = client.post(
        "/api/v1/auth/register",
        {
            "email": email,
            "first_name": "Sensitive",
            "last_name": "Person",
            "phone": phone,
            "password": password,
            "role": "DONOR",
        },
        format="json",
        secure=True,
        HTTP_REFERER="https://testserver/",
        HTTP_X_CSRFTOKEN=csrf,
    )
    assert registration.status_code == 201

    csrf = client.get("/api/v1/auth/csrf", secure=True).json()["csrfToken"]
    failed_login = client.post(
        "/api/v1/auth/login",
        {"email": email, "password": "Incorrect-Private-Password-881!"},
        format="json",
        secure=True,
        HTTP_REFERER="https://testserver/",
        HTTP_X_CSRFTOKEN=csrf,
    )
    assert failed_login.status_code == 401

    for sensitive_value in (email, phone, password, "Incorrect-Private-Password-881!"):
        assert sensitive_value not in caplog.text
