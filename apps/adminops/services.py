"""Administration operations and business rules."""

from uuid import uuid4

from django.contrib.auth import get_user_model
from django.contrib.sessions.models import Session
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.accounts.models import AccountRole
from apps.audit.services import record_event


User = get_user_model()
MANAGED_ROLES = frozenset({AccountRole.STAFF, AccountRole.ADMIN})


class ManagedUserRejected(Exception):
    def __init__(self, code, message, *, status_code, details=None):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)


def _require_admin(actor):
    if (
        not actor.is_authenticated
        or not actor.is_active
        or actor.role != AccountRole.ADMIN
    ):
        raise ManagedUserRejected(
            "forbidden",
            "Only Admin can manage staff accounts.",
            status_code=403,
        )


def _revoke_sessions(user_id):
    session_keys = []
    for session in Session.objects.filter(expire_date__gt=timezone.now()).iterator():
        if session.get_decoded().get("_auth_user_id") == str(user_id):
            session_keys.append(session.session_key)
    if session_keys:
        Session.objects.filter(session_key__in=session_keys).delete()


def create_managed_user(*, actor, email, first_name, last_name, phone, password,
                        role, ip_address=None):
    """Create a Staff or Admin account and audit it atomically."""
    _require_admin(actor)
    if role not in MANAGED_ROLES:
        raise ManagedUserRejected(
            "invalid_role",
            "Only Staff and Admin roles are managed here.",
            status_code=400,
            details={"role": ["Invalid managed role."]},
        )

    normalized_email = User.objects.normalize_email(email).casefold()
    with transaction.atomic():
        try:
            with transaction.atomic():
                user = User.objects.create_user(
                    username=uuid4().hex,
                    email=normalized_email,
                    first_name=first_name,
                    last_name=last_name,
                    phone=phone,
                    role=role,
                    is_active=True,
                    is_staff=False,
                    is_superuser=False,
                    password=password,
                )
        except IntegrityError as exc:
            if User.objects.filter(email__iexact=normalized_email).exists():
                field = "email"
            elif User.objects.filter(phone=phone).exists():
                field = "phone"
            else:
                raise
            raise ManagedUserRejected(
                "duplicate_account",
                "A managed account value is already in use.",
                status_code=400,
                details={field: ["Already in use."]},
            ) from exc
        record_event(
            action="USER_CREATED",
            actor=actor,
            entity_type="USER",
            entity_id=user.pk,
            outcome="SUCCESS",
            ip_address=ip_address,
        )
        return user


def update_managed_user(*, actor, user_id, changes, ip_address=None):
    """Update managed role/activity fields and revoke disabled sessions atomically."""
    _require_admin(actor)
    if not changes or set(changes) - {"is_active", "role"}:
        raise ManagedUserRejected(
            "invalid_update",
            "Only active state and managed role can be changed.",
            status_code=400,
        )
    if "role" in changes and changes["role"] not in MANAGED_ROLES:
        raise ManagedUserRejected(
            "invalid_role",
            "Only Staff and Admin roles are managed here.",
            status_code=400,
            details={"role": ["Invalid managed role."]},
        )

    with transaction.atomic():
        try:
            user = User.objects.select_for_update().get(
                pk=user_id,
                role__in=MANAGED_ROLES,
            )
        except (User.DoesNotExist, TypeError, ValueError) as exc:
            raise ManagedUserRejected(
                "managed_user_not_found",
                "Managed account was not found.",
                status_code=404,
            ) from exc

        update_fields = []
        role_changed = "role" in changes and changes["role"] != user.role
        active_changed = (
            "is_active" in changes and changes["is_active"] != user.is_active
        )
        if role_changed:
            user.role = changes["role"]
            update_fields.append("role")
        if active_changed:
            user.is_active = changes["is_active"]
            update_fields.append("is_active")
        if update_fields:
            user.save(update_fields=tuple(update_fields))

        if active_changed and not user.is_active:
            _revoke_sessions(user.pk)
            record_event(
                action="USER_DISABLED",
                actor=actor,
                entity_type="USER",
                entity_id=user.pk,
                outcome="SUCCESS",
                ip_address=ip_address,
            )
        elif active_changed:
            record_event(
                action="USER_ENABLED",
                actor=actor,
                entity_type="USER",
                entity_id=user.pk,
                outcome="SUCCESS",
                ip_address=ip_address,
            )
        if role_changed:
            record_event(
                action="ROLE_CHANGED",
                actor=actor,
                entity_type="USER",
                entity_id=user.pk,
                outcome="SUCCESS",
                ip_address=ip_address,
            )
        return user
