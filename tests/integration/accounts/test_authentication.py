from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.contrib.sessions.models import Session
from django.db.utils import NotSupportedError
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import LoginThrottle
from apps.accounts.services import login_retry_after, record_failed_login
from apps.audit.models import AuditEvent


pytestmark = pytest.mark.django_db

CSRF_URL = "/api/v1/auth/csrf"
LOGIN_URL = "/api/v1/auth/login"
LOGOUT_URL = "/api/v1/auth/logout"
PASSWORD = "Safe-Long-Password-532!"


def create_user(email="user@example.test", role="DONOR", **overrides):
    fields = {
        "username": email,
        "email": email,
        "first_name": "Test",
        "last_name": "User",
        "phone": f"+1202555{get_user_model().objects.count() + 1:04d}",
        "role": role,
        "password": PASSWORD,
    }
    fields.update(overrides)
    return get_user_model().objects.create_user(**fields)


def csrf_client():
    client = APIClient(enforce_csrf_checks=True)
    response = client.get(CSRF_URL, secure=True)
    assert response.status_code == 200
    assert "csrftoken" in client.cookies
    return client, response.json()["csrfToken"]


def post_login(client, token, email="user@example.test", password=PASSWORD):
    return client.post(
        LOGIN_URL,
        {"email": email, "password": password},
        format="json",
        secure=True,
        HTTP_REFERER="https://testserver/",
        HTTP_X_CSRFTOKEN=token,
    )


def authenticated_client(user):
    client, token = csrf_client()
    assert post_login(client, token, email=user.email).status_code == 200
    token = client.get(CSRF_URL, secure=True).json()["csrfToken"]
    return client, token


@pytest.mark.parametrize(
    ("role", "redirect"),
    [
        ("DONOR", "/donor/dashboard"),
        ("RECIPIENT", "/recipient/dashboard"),
        ("STAFF", "/staff/dashboard"),
        ("ADMIN", "/admin/dashboard"),
    ],
)
def test_login_creates_secure_session_and_redirects_by_role(role, redirect):
    user = create_user(email=f"{role.lower()}@example.test", role=role)
    client, token = csrf_client()

    response = post_login(client, token, email=user.email)

    assert response.status_code == 200
    assert response.json() == {
        "user": {"id": user.pk, "name": "Test User", "role": role},
        "redirect": redirect,
        "session_expires_in": 1200,
    }
    cookie = response.cookies["sessionid"]
    assert cookie["httponly"] is True
    assert cookie["secure"] is True
    assert cookie["samesite"] == "Lax"
    assert cookie["max-age"] == 1200
    event = AuditEvent.objects.get(action="LOGIN_SUCCESS")
    assert event.actor_id == user.pk
    assert event.ip_address == "127.0.0.1"
    assert not hasattr(event, "password")
    assert not hasattr(event, "session_key")


def test_login_failures_are_generic_for_unknown_wrong_and_disabled_accounts():
    active = create_user(email="user@example.test")
    disabled = create_user(email="disabled@example.test", is_active=False)
    client, token = csrf_client()

    unknown = post_login(client, token, email="unknown@example.test", password="wrong")
    wrong_password = post_login(client, token, email="user@example.test", password="wrong")
    disabled_account = post_login(client, token, email=disabled.email, password=PASSWORD)

    responses = (unknown, wrong_password, disabled_account)
    assert all(response.status_code == 401 for response in responses)
    assert {(r.json()["error"]["code"], r.json()["error"]["message"]) for r in responses} == {
        ("invalid_credentials", "Email or password is incorrect.")
    }
    failed_actors = list(
        AuditEvent.objects.filter(action="LOGIN_FAILED")
        .order_by("id")
        .values_list("actor_id", flat=True)
    )
    assert failed_actors == [None, active.pk, disabled.pk]


@override_settings(LOGIN_THROTTLE_ATTEMPTS=2, LOGIN_THROTTLE_WINDOW_SECONDS=30)
def test_repeated_login_failures_return_retry_after_and_store_only_hashed_keys():
    client, token = csrf_client()
    email = "guess@example.test"

    assert post_login(client, token, email=email, password="wrong").status_code == 401
    assert post_login(client, token, email=email, password="wrong").status_code == 401
    response = post_login(client, token, email=email, password="wrong")

    assert response.status_code == 429
    assert response.json()["error"]["code"] == "too_many_attempts"
    assert 1 <= int(response["Retry-After"]) <= 30
    keys = list(LoginThrottle.objects.values_list("key_hash", flat=True))
    assert len(keys) == 2
    assert all(len(key) == 64 and email not in key and "127.0.0.1" not in key for key in keys)


@override_settings(LOGIN_THROTTLE_ATTEMPTS=2, LOGIN_THROTTLE_WINDOW_SECONDS=30)
def test_login_throttle_resets_at_window_boundary():
    now = timezone.now()
    email = "window@example.test"
    record_failed_login(email=email, ip_address="127.0.0.1", now=now)
    record_failed_login(email=email, ip_address="127.0.0.1", now=now)
    assert login_retry_after(email=email, ip_address="127.0.0.1", now=now) == 30

    after_window = now + timedelta(seconds=31)
    assert login_retry_after(email=email, ip_address="127.0.0.1", now=after_window) is None
    record_failed_login(email=email, ip_address="127.0.0.1", now=after_window)

    assert all(record.failed_attempts == 1 for record in LoginThrottle.objects.all())
    assert all(record.blocked_until is None for record in LoginThrottle.objects.all())


def test_successful_login_clears_account_failures_but_preserves_ip_budget():
    create_user()
    client, token = csrf_client()
    post_login(client, token, password="wrong")
    assert LoginThrottle.objects.count() == 2

    response = post_login(client, token)

    assert response.status_code == 200
    assert LoginThrottle.objects.count() == 1


def test_login_uses_email_even_when_username_is_different():
    user = create_user(email="contact@example.test", username="display-handle")
    client, token = csrf_client()

    response = post_login(client, token, email=user.email)

    assert response.status_code == 200
    assert response.json()["user"]["id"] == user.pk


def test_login_rotates_a_preexisting_anonymous_session_key():
    user = create_user()
    client, token = csrf_client()
    client.session["untrusted_marker"] = "anonymous-session"
    client.session.save()
    anonymous_session_key = client.session.session_key
    assert Session.objects.filter(session_key=anonymous_session_key).exists()

    response = post_login(client, token)

    assert response.status_code == 200
    authenticated_session_key = client.cookies["sessionid"].value
    assert authenticated_session_key != anonymous_session_key
    assert not Session.objects.filter(session_key=anonymous_session_key).exists()
    authenticated_session = Session.objects.get(session_key=authenticated_session_key)
    assert authenticated_session.get_decoded()["_auth_user_id"] == str(user.pk)


def test_logout_requires_csrf_and_invalidates_active_session():
    user = create_user()
    client, token = csrf_client()
    assert post_login(client, token).status_code == 200
    session_key = client.cookies["sessionid"].value
    assert Session.objects.filter(session_key=session_key).exists()
    # Login rotates the CSRF token along with the session key.
    token = client.get(CSRF_URL, secure=True).json()["csrfToken"]
    missing_csrf = client.post(
        LOGOUT_URL,
        {},
        format="json",
        secure=True,
        HTTP_REFERER="https://testserver/",
    )
    assert missing_csrf.status_code == 403
    assert missing_csrf.json()["error"]["code"] == "csrf_failed"

    response = client.post(
        LOGOUT_URL,
        {},
        format="json",
        secure=True,
        HTTP_REFERER="https://testserver/",
        HTTP_X_CSRFTOKEN=token,
    )

    assert response.status_code == 204
    assert "_auth_user_id" not in client.session
    assert not Session.objects.filter(session_key=session_key).exists()
    assert (
        AuditEvent.objects.filter(
            action="LOGIN_SUCCESS",
            actor=user,
            ip_address="127.0.0.1",
        ).count()
        == 1
    )


def test_state_changing_account_endpoints_reject_missing_csrf_token():
    client = APIClient(enforce_csrf_checks=True)

    login = client.post(
        LOGIN_URL,
        {"email": "x@example.test", "password": PASSWORD},
        format="json",
        secure=True,
    )
    registration = client.post(
        "/api/v1/auth/register",
        {
            "email": "new@example.test",
            "first_name": "New",
            "last_name": "User",
            "phone": "+442079460123",
            "password": PASSWORD,
            "role": "DONOR",
        },
        format="json",
        secure=True,
    )

    assert login.status_code == 403
    assert login.json()["error"]["code"] == "csrf_failed"
    assert registration.status_code == 403
    assert registration.json()["error"]["code"] == "csrf_failed"
    assert get_user_model().objects.count() == 0


def test_csrf_token_allows_public_registration():
    client, token = csrf_client()
    response = client.post(
        "/api/v1/auth/register",
        {
            "email": "csrf@example.test",
            "first_name": "Csrf",
            "last_name": "Checked",
            "phone": "+442079460123",
            "password": PASSWORD,
            "role": "DONOR",
        },
        format="json",
        secure=True,
        HTTP_REFERER="https://testserver/",
        HTTP_X_CSRFTOKEN=token,
    )
    assert response.status_code == 201


def test_audit_events_reject_updates_and_deletes():
    event = AuditEvent.objects.create(action="LOGIN_FAILED")

    event.action = "LOGIN_SUCCESS"
    with pytest.raises(ValidationError):
        event.save()
    with pytest.raises(ValidationError):
        event.delete()
    with pytest.raises(NotSupportedError):
        AuditEvent.objects.filter(pk=event.pk).update(action="LOGIN_SUCCESS")
    with pytest.raises(NotSupportedError):
        AuditEvent.objects.filter(pk=event.pk).delete()


def test_csrf_cookie_is_set_by_token_endpoint():
    client, token = csrf_client()

    assert token
    assert client.cookies["csrftoken"]["secure"] is True
    assert client.cookies["csrftoken"]["samesite"] == "Lax"


def test_idle_timeout_expires_database_session_and_records_event():
    user = create_user()
    client, _ = authenticated_client(user)
    session_key = client.cookies["sessionid"].value
    Session.objects.filter(session_key=session_key).update(
        expire_date=timezone.now() - timedelta(seconds=1)
    )

    response = client.post(
        LOGOUT_URL,
        {},
        format="json",
        secure=True,
        HTTP_REFERER="https://testserver/",
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "session_expired"
    assert response.cookies["sessionid"]["max-age"] == 0
    assert AuditEvent.objects.filter(action="SESSION_EXPIRED", actor__isnull=True).exists()


def test_authenticated_activity_slides_idle_expiration():
    user = create_user()
    client, _ = authenticated_client(user)
    session_key = client.cookies["sessionid"].value
    session = Session.objects.get(session_key=session_key)
    Session.objects.filter(pk=session.pk).update(
        expire_date=timezone.now() + timedelta(seconds=10)
    )
    near_expiry = Session.objects.get(pk=session.pk).expire_date

    response = client.get(CSRF_URL, secure=True)

    assert response.status_code == 200
    renewed = Session.objects.get(session_key=session_key).expire_date
    assert renewed > near_expiry


@override_settings(SESSION_ABSOLUTE_TIMEOUT_SECONDS=10)
def test_absolute_timeout_expires_active_session_and_records_actor():
    user = create_user()
    client, _ = authenticated_client(user)
    session = client.session
    session["auth_started_at"] = timezone.now().timestamp() - 11
    session.save()

    response = client.post(
        LOGOUT_URL,
        {},
        format="json",
        secure=True,
        HTTP_REFERER="https://testserver/",
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "session_expired"
    assert AuditEvent.objects.filter(action="SESSION_EXPIRED", actor=user).exists()


@pytest.mark.parametrize("role", ["DONOR", "RECIPIENT", "STAFF", "ADMIN"])
@override_settings(SESSION_ABSOLUTE_TIMEOUT_SECONDS=10)
def test_every_role_receives_readable_expiry_response_on_protected_api(role):
    user = create_user(email=f"expired-{role.lower()}@example.test", role=role)
    client, _ = authenticated_client(user)
    session = client.session
    session["auth_started_at"] = timezone.now().timestamp() - 11
    session.save()

    response = client.get("/api/v1/users/me", secure=True)

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "session_expired"
    assert response.json()["error"]["message"] == "Your session expired. Please sign in again."
    assert response.cookies["sessionid"]["max-age"] == 0
    assert AuditEvent.objects.filter(action="SESSION_EXPIRED", actor=user).count() == 1


def test_concurrent_sessions_are_independent_and_disabled_account_expires():
    user = create_user()
    first, first_token = authenticated_client(user)
    second, _ = authenticated_client(user)
    first_session = first.cookies["sessionid"].value
    second_session = second.cookies["sessionid"].value
    assert first_session != second_session

    logged_out = first.post(
        LOGOUT_URL,
        {},
        format="json",
        secure=True,
        HTTP_REFERER="https://testserver/",
        HTTP_X_CSRFTOKEN=first_token,
    )
    assert logged_out.status_code == 204
    assert second.get(CSRF_URL, secure=True).status_code == 200
    assert Session.objects.filter(session_key=second_session).exists()

    user.is_active = False
    user.save(update_fields=("is_active",))
    expired = second.post(
        LOGOUT_URL,
        {},
        format="json",
        secure=True,
        HTTP_REFERER="https://testserver/",
    )
    assert expired.status_code == 401
    assert expired.json()["error"]["code"] == "session_expired"


def test_auth_endpoints_reject_unexpected_query_parameters_and_body_fields():
    client = APIClient()
    login = client.post(f"{LOGIN_URL}?next=https://evil.test", {"email": "x@example.test", "password": PASSWORD}, format="json")
    csrf = client.get(f"{CSRF_URL}?token=unexpected")

    assert login.status_code == 400
    assert login.json()["error"]["code"] == "invalid_query"
    assert csrf.status_code == 400
    assert csrf.json()["error"]["code"] == "invalid_query"


def test_logout_rejects_unexpected_body_fields():
    create_user()
    client, token = csrf_client()
    assert post_login(client, token).status_code == 200
    token = client.get(CSRF_URL, secure=True).json()["csrfToken"]

    response = client.post(
        LOGOUT_URL,
        {"redirect": "https://evil.test"},
        format="json",
        secure=True,
        HTTP_REFERER="https://testserver/",
        HTTP_X_CSRFTOKEN=token,
    )

    assert response.status_code == 400
    assert response.json()["error"]["details"]["non_field_errors"] == [
        "Unexpected fields are not allowed."
    ]
