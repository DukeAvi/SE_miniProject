"""Transactional donation recording operations."""

from datetime import date
from uuid import uuid4
from zoneinfo import ZoneInfo

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import AccountRole
from apps.audit.services import record_event

from .eligibility import check_donor_eligibility
from .models import Donation, DonorProfile


class DonationRejected(Exception):
    def __init__(self, code: str, message: str, details=None):
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(message)


def record_completed_donation(*, actor, donor_id: int, donation_date: date,
                              blood_group: str, component: str, quantity_units: int,
                              screening_weight_kg, ip_address=None) -> Donation:
    """Record a completed, eligible donation with its profile and audit update atomically."""
    if not actor.is_authenticated or actor.role != AccountRole.STAFF:
        raise DonationRejected("forbidden", "Only Staff can record donations.")
    if component != Donation.Component.WHOLE_BLOOD:
        raise DonationRejected("donation_type_unsupported", "Only whole-blood donations are supported.")

    zone = ZoneInfo(getattr(settings, "BLOOD_BANK_TIME_ZONE", "Asia/Kolkata"))
    local_today = timezone.now().astimezone(zone).date()
    if donation_date > local_today:
        raise DonationRejected("invalid_donation_date", "Donation date cannot be in the future.")

    with transaction.atomic():
        try:
            profile = DonorProfile.objects.select_for_update().select_related("user").get(user_id=donor_id)
        except DonorProfile.DoesNotExist as exc:
            raise DonationRejected("donor_not_found", "Donor was not found.") from exc
        if profile.user.role != AccountRole.DONOR:
            raise DonationRejected("donor_not_found", "Donor was not found.")
        result = check_donor_eligibility(
            birth_date=profile.birth_date,
            weight_kg=screening_weight_kg,
            on_date=donation_date,
            last_whole_blood_donation=profile.last_donation_date,
            donation_type="WHOLE_BLOOD",
            timezone_name=zone.key,
        )
        if not result.eligible:
            raise DonationRejected("donor_ineligible", "Donor is not eligible to donate.", result.as_dict())
        if blood_group != profile.blood_group:
            raise DonationRejected("blood_group_mismatch", "Recorded blood group must match the donor profile.")

        donation = Donation.objects.create(
            id=uuid4(), donor=profile, donation_date=donation_date,
            blood_group=blood_group, component=component,
            quantity_units=quantity_units, screening_weight_kg=screening_weight_kg,
        )
        profile.last_donation_date = donation_date
        profile.save(update_fields=("last_donation_date", "updated_at"))
        record_event(action="DONATION_RECORDED", actor=actor, ip_address=ip_address)
        return donation
