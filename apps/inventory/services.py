"""Transactional blood-unit inventory operations."""

from zoneinfo import ZoneInfo

from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.accounts.models import AccountRole
from apps.audit.services import record_event
from apps.donors.models import Donation

from .models import BloodUnit, InventoryTransaction


class BloodUnitRejected(Exception):
    def __init__(self, code, message, *, status_code, details=None):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)


TRANSITIONS = {
    InventoryTransaction.Action.RESERVE: (BloodUnit.Status.AVAILABLE, BloodUnit.Status.RESERVED),
    InventoryTransaction.Action.RELEASE: (BloodUnit.Status.RESERVED, BloodUnit.Status.AVAILABLE),
    InventoryTransaction.Action.ISSUE: (BloodUnit.Status.RESERVED, BloodUnit.Status.ISSUED),
    InventoryTransaction.Action.DISCARD: (BloodUnit.Status.AVAILABLE, BloodUnit.Status.DISCARDED),
    InventoryTransaction.Action.RETURN: (BloodUnit.Status.ISSUED, BloodUnit.Status.RETURNED),
}


def blood_bank_today():
    return timezone.localdate(timezone=ZoneInfo(settings.BLOOD_BANK_TIME_ZONE))


def available_stock_count(*, blood_group, component, as_of_date=None):
    """Derive stock from unexpired AVAILABLE records; no mutable counter exists."""
    as_of_date = as_of_date or blood_bank_today()
    return BloodUnit.objects.filter(
        blood_group=blood_group,
        component=component,
        status=BloodUnit.Status.AVAILABLE,
        expiry_date__gt=as_of_date,
    ).count()


def transition_blood_unit(*, actor, unit_id, action, reason, ip_address=None, as_of_date=None):
    """Lock a unit and append its ledger and audit records atomically."""
    if actor is not None and (not actor.is_authenticated or actor.role != AccountRole.STAFF):
        raise BloodUnitRejected("forbidden", "Only Staff can change inventory status.", status_code=403)
    if actor is None and action != InventoryTransaction.Action.EXPIRE:
        raise BloodUnitRejected("forbidden", "An actor is required for this inventory action.", status_code=403)
    if not isinstance(reason, str) or not reason.strip():
        raise BloodUnitRejected("invalid_reason", "A reason is required.", status_code=400, details={"reason": ["This field is required."]})

    today = as_of_date or blood_bank_today()
    with transaction.atomic():
        try:
            unit = BloodUnit.objects.select_for_update().get(pk=unit_id)
        except (BloodUnit.DoesNotExist, ValueError, TypeError) as exc:
            raise BloodUnitRejected("unit_not_found", "Blood unit was not found.", status_code=404) from exc

        if action == InventoryTransaction.Action.EXPIRE:
            if unit.status not in (BloodUnit.Status.AVAILABLE, BloodUnit.Status.RESERVED) or unit.expiry_date > today:
                raise BloodUnitRejected(
                    "invalid_state_transition",
                    "Only an available or reserved unit at or past expiry can be expired.",
                    status_code=409,
                )
            target_status = BloodUnit.Status.EXPIRED
        else:
            transition = TRANSITIONS.get(action)
            if transition is None or unit.status != transition[0]:
                raise BloodUnitRejected("invalid_state_transition", "This blood-unit state transition is not allowed.", status_code=409)
            if action in (InventoryTransaction.Action.RESERVE, InventoryTransaction.Action.ISSUE) and unit.expiry_date <= today:
                raise BloodUnitRejected("unit_unavailable", "Expired units cannot be reserved or issued.", status_code=409)
            target_status = transition[1]

        previous_status = unit.status
        unit.status = target_status
        unit.save(update_fields=("status",))
        InventoryTransaction.objects.create(
            blood_unit=unit,
            action=action,
            from_status=previous_status,
            to_status=target_status,
            actor=actor,
            reason=reason.strip(),
        )
        event_action = {
            InventoryTransaction.Action.RESERVE: "UNIT_RESERVED",
            InventoryTransaction.Action.RELEASE: "UNIT_RELEASED",
            InventoryTransaction.Action.ISSUE: "UNIT_ISSUED",
            InventoryTransaction.Action.EXPIRE: "UNIT_EXPIRED",
            InventoryTransaction.Action.DISCARD: "UNIT_DISCARDED",
            InventoryTransaction.Action.RETURN: "UNIT_RETURNED",
        }[action]
        record_event(action=event_action, actor=actor, ip_address=ip_address)
        return unit


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
