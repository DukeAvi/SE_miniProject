from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models.functions import Lower


class AccountRole(models.TextChoices):
    DONOR = "DONOR", "Donor"
    RECIPIENT = "RECIPIENT", "Recipient"
    STAFF = "STAFF", "Staff"
    ADMIN = "ADMIN", "Admin"


class User(AbstractUser):
    email = models.EmailField(unique=True)
    # Nullable only for accounts that predate the profile fields; registration
    # always requires both values and authorization denies an unset role.
    phone = models.CharField(max_length=16, unique=True, null=True, blank=True)
    role = models.CharField(max_length=10, choices=AccountRole.choices, null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(Lower("email"), name="accounts_user_email_ci_unique")
        ]


class LoginThrottle(models.Model):
    """Failed-login window keyed by a secret HMAC, not raw email or IP data."""

    key_hash = models.CharField(max_length=64, unique=True)
    failed_attempts = models.PositiveSmallIntegerField(default=0)
    window_started_at = models.DateTimeField()
    blocked_until = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=("blocked_until",))]
