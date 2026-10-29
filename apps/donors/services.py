"""Transactional donation recording operations."""

from datetime import date
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import AccountRole
from apps.audit.services import record_event

from .eligibility import check_donor_eligibility
from .models import Appointment, Donation, DonationSlot, DonorProfile


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


class AppointmentRejected(Exception):
    def __init__(self, code: str, message: str, *, status_code: int, details=None):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)


def book_appointment(*, actor, slot_id, ip_address=None) -> Appointment:
    """Book an available slot after checking the donor with the shared engine."""
    if not actor.is_authenticated or actor.role != AccountRole.DONOR:
        raise AppointmentRejected("forbidden", "Only Donors can book appointments.", status_code=403)
    zone = ZoneInfo(getattr(settings, "BLOOD_BANK_TIME_ZONE", "Asia/Kolkata"))
    with transaction.atomic():
        try:
            slot = DonationSlot.objects.select_for_update().get(pk=slot_id)
        except DonationSlot.DoesNotExist as exc:
            raise AppointmentRejected("slot_not_found", "Donation slot was not found.", status_code=404) from exc
        try:
            profile = DonorProfile.objects.select_for_update().get(user=actor)
        except DonorProfile.DoesNotExist as exc:
            raise AppointmentRejected("donor_profile_not_found", "Donor profile was not found.", status_code=404) from exc
        if slot.starts_at <= timezone.now():
            raise AppointmentRejected("slot_unavailable", "Donation slot is no longer available.", status_code=409)
        eligibility = check_donor_eligibility(
            birth_date=profile.birth_date,
            weight_kg=profile.weight_kg,
            on_date=slot.starts_at,
            last_whole_blood_donation=profile.last_donation_date,
            donation_type="WHOLE_BLOOD",
            timezone_name=zone.key,
        )
        if not eligibility.eligible:
            raise AppointmentRejected("donor_ineligible", "Donor is not eligible for this appointment.", status_code=422, details=eligibility.as_dict())
        active = Appointment.objects.filter(slot=slot, status=Appointment.Status.BOOKED)
        if active.filter(donor=profile).exists():
            raise AppointmentRejected("duplicate_appointment", "Donor already has an active booking for this slot.", status_code=409)
        if active.count() >= slot.capacity:
            raise AppointmentRejected("slot_full", "Donation slot is full.", status_code=409)
        appointment = Appointment.objects.create(donor=profile, slot=slot)
        record_event(action="APPOINTMENT_BOOKED", actor=actor, ip_address=ip_address)
        return appointment


def cancel_appointment(*, actor, appointment_id, ip_address=None) -> Appointment:
    """Cancel an owned BOOKED appointment, retaining the appointment history."""
    if not actor.is_authenticated or actor.role != AccountRole.DONOR:
        raise AppointmentRejected("forbidden", "Only Donors can cancel appointments.", status_code=403)
    try:
        appointment_id = UUID(str(appointment_id))
    except (TypeError, ValueError) as exc:
        raise AppointmentRejected("appointment_not_found", "Appointment was not found.", status_code=404) from exc
    with transaction.atomic():
        try:
            appointment_ref = Appointment.objects.only("slot_id").get(pk=appointment_id, donor__user=actor)
        except Appointment.DoesNotExist as exc:
            record_event(action="ACCESS_DENIED", actor=actor, ip_address=ip_address)
            raise AppointmentRejected("appointment_not_found", "Appointment was not found.", status_code=404) from exc
        DonationSlot.objects.select_for_update().get(pk=appointment_ref.slot_id)
        appointment = Appointment.objects.select_for_update().get(pk=appointment_id, donor__user=actor)
        if appointment.status != Appointment.Status.BOOKED:
            raise AppointmentRejected("invalid_appointment_state", "Only booked appointments can be cancelled.", status_code=409)
        appointment.status = Appointment.Status.CANCELLED
        appointment.cancelled_at = timezone.now()
        appointment.save(update_fields=("status", "cancelled_at"))
        record_event(action="APPOINTMENT_CANCELLED", actor=actor, ip_address=ip_address)
        return appointment
