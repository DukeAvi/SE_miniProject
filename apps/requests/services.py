"""Blood request operations and business rules."""

from uuid import uuid4

from django.db import transaction
from django.utils import timezone

from apps.accounts.models import AccountRole
from apps.audit.services import record_event

from .models import BloodRequest


class BloodRequestRejected(Exception):
    def __init__(self, code, message, *, status_code, details=None):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)


def submit_blood_request(*, actor, patient_name, patient_blood_group, component,
                         units_needed, urgency, hospital, required_by,
                         contact_phone, ip_address=None):
    """Create a pending request and its protected audit event atomically."""
    if (
        not actor.is_authenticated
        or not actor.is_active
        or actor.role != AccountRole.RECIPIENT
    ):
        raise BloodRequestRejected(
            "forbidden",
            "Only Recipients can submit blood requests.",
            status_code=403,
        )
    if required_by <= timezone.now():
        raise BloodRequestRejected(
            "invalid_required_by",
            "Required-by time must be in the future.",
            status_code=400,
            details={"required_by": ["Must be in the future."]},
        )

    request_uuid = uuid4()
    request_number = f"REQ-{timezone.now().year}-{request_uuid.hex[:16].upper()}"
    with transaction.atomic():
        blood_request = BloodRequest.objects.create(
            id=request_uuid,
            request_id=request_number,
            requester=actor,
            patient_name=patient_name,
            patient_blood_group=patient_blood_group,
            component=component,
            units_needed=units_needed,
            urgency=urgency,
            hospital=hospital,
            required_by=required_by,
            contact_phone=contact_phone,
            status=BloodRequest.Status.PENDING,
        )
        record_event(
            action="REQUEST_SUBMITTED",
            actor=actor,
            entity_type="BLOOD_REQUEST",
            entity_id=blood_request.pk,
            ip_address=ip_address,
        )
        return blood_request
