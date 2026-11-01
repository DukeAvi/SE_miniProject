"""Blood request operations and business rules."""

from uuid import uuid4

from django.db import transaction
from django.utils import timezone

from apps.accounts.models import AccountRole
from apps.audit.services import record_event
from apps.notifications.models import Notification

from .models import BloodRequest


class BloodRequestRejected(Exception):
    def __init__(self, code, message, *, status_code, details=None):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)


DECISIONS = {
    "APPROVE": (
        BloodRequest.Status.APPROVED,
        "REQUEST_APPROVED",
        Notification.Type.REQUEST_APPROVED,
    ),
    "REJECT": (
        BloodRequest.Status.REJECTED,
        "REQUEST_REJECTED",
        Notification.Type.REQUEST_REJECTED,
    ),
    "HOLD": (
        BloodRequest.Status.ON_HOLD,
        "REQUEST_HELD",
        Notification.Type.REQUEST_HELD,
    ),
}


def decide_blood_request(*, actor, request_id, decision, reason="", ip_address=None):
    """Apply a Staff decision and create its audit and outbox rows atomically."""
    if (
        not actor.is_authenticated
        or not actor.is_active
        or actor.role != AccountRole.STAFF
    ):
        raise BloodRequestRejected(
            "forbidden",
            "Only Staff can review blood requests.",
            status_code=403,
        )

    transition = DECISIONS.get(decision)
    if transition is None:
        raise BloodRequestRejected(
            "invalid_decision",
            "Decision must be APPROVE, REJECT, or HOLD.",
            status_code=400,
            details={"decision": ["Invalid choice."]},
        )
    if reason is None:
        reason = ""
    if not isinstance(reason, str) or len(reason) > 500:
        raise BloodRequestRejected(
            "invalid_reason",
            "Reason must be text no longer than 500 characters.",
            status_code=400,
            details={"reason": ["Must be text no longer than 500 characters."]},
        )
    reason = reason.strip()
    if decision in ("REJECT", "HOLD") and not reason:
        raise BloodRequestRejected(
            "reason_required",
            "A reason is required when rejecting or holding a request.",
            status_code=400,
            details={"reason": ["This field is required."]},
        )

    target_status, audit_action, notification_type = transition
    with transaction.atomic():
        try:
            blood_request = (
                BloodRequest.objects.select_for_update()
                .select_related("requester")
                .get(request_id=request_id)
            )
        except BloodRequest.DoesNotExist as exc:
            raise BloodRequestRejected(
                "request_not_found",
                "Blood request was not found.",
                status_code=404,
            ) from exc

        if blood_request.status != BloodRequest.Status.PENDING:
            raise BloodRequestRejected(
                "invalid_state_transition",
                "Only a pending blood request can be reviewed.",
                status_code=409,
            )

        blood_request.status = target_status
        blood_request.reviewer = actor
        blood_request.reviewed_at = timezone.now()
        blood_request.decision_reason = reason
        blood_request.save(
            update_fields=("status", "reviewer", "reviewed_at", "decision_reason")
        )
        record_event(
            action=audit_action,
            actor=actor,
            entity_type="BLOOD_REQUEST",
            entity_id=blood_request.pk,
            ip_address=ip_address,
        )
        Notification.objects.create(
            recipient=blood_request.requester,
            blood_request=blood_request,
            type=notification_type,
        )
        return blood_request


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
