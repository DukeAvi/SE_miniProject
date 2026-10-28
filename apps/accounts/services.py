"""Account operations and business rules."""

import math
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import authenticate, get_user_model, login as auth_login
from django.db import IntegrityError, transaction
from django.utils import timezone
from django.utils.crypto import salted_hmac

from apps.audit.services import record_event

from .models import LoginThrottle


DASHBOARD_PATHS = {
    "DONOR": "/donor/dashboard",
    "RECIPIENT": "/recipient/dashboard",
    "STAFF": "/staff/dashboard",
    "ADMIN": "/admin/dashboard",
}


class DuplicateAccountValue(Exception):
    """A normalized email address or phone number is already registered."""

    def __init__(self, field: str):
        self.field = field
        super().__init__(field)


def register_account(*, email: str, first_name: str, last_name: str, phone: str,
                     password: str, role: str):
    """Create a public Donor or Recipient account atomically."""
    User = get_user_model()
    normalized_email = User.objects.normalize_email(email).casefold()

    try:
        with transaction.atomic():
            return User.objects.create_user(
                username=normalized_email,
                email=normalized_email,
                first_name=first_name,
                last_name=last_name,
                phone=phone,
                role=role,
                is_staff=False,
                is_superuser=False,
                password=password,
            )
    except IntegrityError as error:
        if User.objects.filter(email__iexact=normalized_email).exists():
            raise DuplicateAccountValue("email") from error
        if User.objects.filter(phone=phone).exists():
            raise DuplicateAccountValue("phone") from error
        raise


def _login_throttle_key(value: str) -> str:
    return salted_hmac(
        "accounts.login-throttle",
        value,
        secret=settings.SECRET_KEY,
        algorithm="sha256",
    ).hexdigest()


def _login_throttle_keys(email: str, ip_address: str) -> tuple[str, str]:
    return (
        _login_throttle_key(f"email:{email.casefold()}"),
        _login_throttle_key(f"ip:{ip_address or 'unknown'}"),
    )


def login_retry_after(*, email: str, ip_address: str, now=None) -> int | None:
    now = now or timezone.now()
    blocked_until = (
        LoginThrottle.objects.filter(
            key_hash__in=_login_throttle_keys(email, ip_address),
            blocked_until__gt=now,
        )
        .order_by("-blocked_until")
        .values_list("blocked_until", flat=True)
        .first()
    )
    if blocked_until is None:
        return None
    return max(1, math.ceil((blocked_until - now).total_seconds()))


def record_failed_login(*, email: str, ip_address: str, now=None) -> None:
    now = now or timezone.now()
    window = settings.LOGIN_THROTTLE_WINDOW_SECONDS
    threshold = settings.LOGIN_THROTTLE_ATTEMPTS
    for key_hash in _login_throttle_keys(email, ip_address):
        with transaction.atomic():
            record, created = (
                LoginThrottle.objects.select_for_update().get_or_create(
                    key_hash=key_hash,
                    defaults={"failed_attempts": 0, "window_started_at": now},
                )
            )
            if not created and (now - record.window_started_at).total_seconds() >= window:
                record.failed_attempts = 0
                record.window_started_at = now
                record.blocked_until = None
            record.failed_attempts += 1
            if record.failed_attempts >= threshold:
                record.blocked_until = now + timedelta(seconds=window)
            record.save(
                update_fields=("failed_attempts", "window_started_at", "blocked_until")
            )


def clear_login_failures(*, email: str) -> None:
    email_key = _login_throttle_key(f"email:{email.casefold()}")
    LoginThrottle.objects.filter(key_hash=email_key).delete()


def record_login_event(*, action: str, actor=None, ip_address: str | None = None) -> None:
    record_event(action=action, actor=actor, ip_address=ip_address)


def login_account(*, request, email: str, password: str, ip_address: str | None):
    """Authenticate, throttle and audit a login attempt; return (user, retry_after)."""
    retry_after = login_retry_after(email=email, ip_address=ip_address or "")
    if retry_after is not None:
        record_login_event(action="LOGIN_FAILED", ip_address=ip_address)
        return None, retry_after

    user = authenticate(request, username=email, password=password)
    if user is not None and user.role in DASHBOARD_PATHS:
        clear_login_failures(email=email)
        auth_login(request, user)
        record_login_event(action="LOGIN_SUCCESS", actor=user, ip_address=ip_address)
        return user, None

    candidate = get_user_model().objects.filter(email__iexact=email).first()
    record_failed_login(email=email, ip_address=ip_address or "")
    record_login_event(action="LOGIN_FAILED", actor=candidate, ip_address=ip_address)
    return None, None
