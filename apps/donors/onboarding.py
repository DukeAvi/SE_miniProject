"""Staff-authorized donor lookup and initial eligibility-profile provisioning."""

from datetime import date

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.db.models import Exists, OuterRef, Q
from django.utils import timezone
from zoneinfo import ZoneInfo

from apps.accounts.models import AccountRole
from apps.audit.services import record_event

from .models import DonorProfile


class DonorOnboardingRejected(Exception):
    def __init__(self, code: str, message: str, *, status_code: int):
        self.code = code
        self.message = message
        self.status_code = status_code
        super().__init__(message)


def find_donors(*, query: str):
    """Find a small, minimal-information set of active donor accounts."""
    normalized = query.strip()
    if len(normalized) < 2:
        return []

    profiles = DonorProfile.objects.filter(user_id=OuterRef("pk"))
    return (
        get_user_model()
        .objects.filter(role=AccountRole.DONOR, is_active=True)
        .filter(
            Q(email__icontains=normalized)
            | Q(first_name__icontains=normalized)
            | Q(last_name__icontains=normalized)
        )
        .annotate(has_donor_profile=Exists(profiles))
        .order_by("first_name", "last_name", "pk")[:20]
    )


def create_donor_profile(
    *, actor, donor_id: int, birth_date: date, weight_kg, blood_group: str,
    ip_address: str | None = None,
) -> DonorProfile:
    """Create the first verified profile for an active donor, with an audit row."""
    if (
        not actor.is_authenticated
        or not actor.is_active
        or actor.role != AccountRole.STAFF
    ):
        raise DonorOnboardingRejected(
            "forbidden", "Only Staff can complete donor profile verification.", status_code=403
        )

    zone = ZoneInfo(getattr(settings, "BLOOD_BANK_TIME_ZONE", "Asia/Kolkata"))
    today = timezone.now().astimezone(zone).date()
    if birth_date > today:
        raise DonorOnboardingRejected(
            "invalid_birth_date", "Birth date cannot be in the future.", status_code=400
        )

    User = get_user_model()
    with transaction.atomic():
        try:
            donor = User.objects.select_for_update().get(
                pk=donor_id, role=AccountRole.DONOR, is_active=True
            )
        except User.DoesNotExist as exc:
            raise DonorOnboardingRejected(
                "donor_not_found", "Donor was not found.", status_code=404
            ) from exc

        if DonorProfile.objects.filter(user=donor).exists():
            raise DonorOnboardingRejected(
                "profile_already_exists",
                "This donor already has a verified profile.",
                status_code=409,
            )

        try:
            with transaction.atomic():
                profile = DonorProfile.objects.create(
                    user=donor,
                    birth_date=birth_date,
                    weight_kg=weight_kg,
                    blood_group=blood_group,
                )
        except IntegrityError as exc:
            # A concurrent Staff request may have created the one-to-one profile.
            if DonorProfile.objects.filter(user=donor).exists():
                raise DonorOnboardingRejected(
                    "profile_already_exists",
                    "This donor already has a verified profile.",
                    status_code=409,
                ) from exc
            raise

        record_event(
            action="DONOR_PROFILE_CREATED",
            actor=actor,
            entity_type="USER",
            entity_id=donor.pk,
            ip_address=ip_address,
        )
        return profile
