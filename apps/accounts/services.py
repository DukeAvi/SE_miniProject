"""Account operations and business rules."""

from uuid import uuid4

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction


class DuplicateAccountValue(Exception):
    """A normalized email address or phone number is already registered."""

    def __init__(self, field: str):
        self.field = field
        super().__init__(field)


def register_account(*, email: str, first_name: str, last_name: str, phone: str,
                     password: str, role: str):
    """Create a public account with an opaque internal username atomically."""
    User = get_user_model()
    normalized_email = User.objects.normalize_email(email).casefold()

    for _ in range(3):
        internal_username = uuid4().hex
        try:
            with transaction.atomic():
                return User.objects.create_user(
                    username=internal_username,
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
            if User.objects.filter(username=internal_username).exists():
                continue
            raise
    raise RuntimeError("Unable to allocate an internal account identifier.")
