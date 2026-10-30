"""Transactional blood-unit inventory operations."""

from zoneinfo import ZoneInfo

from django.conf import settings
from django.db import IntegrityError, transaction

from apps.accounts.models import AccountRole
from apps.audit.services import record_event
from apps.donors.models import Donation

from .models import BloodUnit


class BloodUnitRejected(Exception):
    def __init__(self, code, message, *, status_code, details=None):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)


def create_verified_blood_unit(*, actor, donation_id, unit_code, blood_group,
                               component, collected_at, expiry_date, quantity_units,
                               ip_address=None):
    """Create a unit for a completed donation and audit it in the same transaction."""
    if not actor.is_authenticated or actor.role != AccountRole.STAFF:
        raise BloodUnitRejected("forbidden", "Only Staff can create blood units.", status_code=403)

    with transaction.atomic():
        try:
            donation = Donation.objects.select_for_update().get(pk=donation_id)
        except (Donation.DoesNotExist, ValueError, TypeError) as exc:
            raise BloodUnitRejected("donation_not_found", "Completed donation was not found.", status_code=404) from exc
        if donation.status != Donation.Status.COMPLETED:
            raise BloodUnitRejected("donation_not_verified", "A completed donation is required.", status_code=422)
        if donation.blood_group != blood_group:
            raise BloodUnitRejected("blood_group_mismatch", "Blood group must match the donation.", status_code=422)
        collection_date = collected_at.astimezone(ZoneInfo(settings.BLOOD_BANK_TIME_ZONE)).date()
        if donation.donation_date != collection_date:
            raise BloodUnitRejected("collection_date_mismatch", "Collection date must match the donation date.", status_code=422)
        if expiry_date <= collection_date:
            raise BloodUnitRejected(
                "invalid_expiry_date",
                "Expiry date must be after the collection date.",
                status_code=422,
                details={"expiry_date": ["Must be after the collection date."]},
            )

        try:
            with transaction.atomic():
                unit = BloodUnit.objects.create(
                    donation=donation,
                    unit_code=unit_code,
                    blood_group=blood_group,
                    component=component,
                    collected_at=collected_at,
                    expiry_date=expiry_date,
                    quantity_units=quantity_units,
                    status=BloodUnit.Status.AVAILABLE,
                )
        except IntegrityError as exc:
            if "unit_code" in str(exc).lower():
                raise BloodUnitRejected("duplicate_unit_code", "Unit code already exists.", status_code=409, details={"unit_code": ["Already in use."]}) from exc
            raise
        record_event(action="UNIT_CREATED", actor=actor, ip_address=ip_address)
        return unit
