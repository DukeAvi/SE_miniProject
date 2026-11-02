"""Blood request operations and business rules."""

from uuid import uuid4

from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.accounts.models import AccountRole
from apps.audit.services import record_event
from apps.inventory.models import BloodUnit, InventoryTransaction
from apps.inventory.serializers import BloodUnitSerializer
from apps.inventory.services import BloodUnitRejected, blood_bank_today, transition_blood_unit
from apps.notifications.models import Notification

from .compatibility import is_compatible, select_compatible_units
from .models import BloodAllocation, BloodRequest, IssueIdempotency


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


def _require_staff(actor):
    if (
        not actor.is_authenticated
        or not actor.is_active
        or actor.role != AccountRole.STAFF
    ):
        raise BloodRequestRejected(
            "forbidden",
            "Only Staff can reserve or issue blood units.",
            status_code=403,
        )


def _as_request_rejection(exc):
    return BloodRequestRejected(
        exc.code,
        exc.message,
        status_code=exc.status_code,
        details=exc.details,
    )


def _unit_response(unit):
    return dict(BloodUnitSerializer(unit).data)


def _lock_request(request_id):
    try:
        return (
            BloodRequest.objects.select_for_update()
            .select_related("requester")
            .get(request_id=request_id)
        )
    except (BloodRequest.DoesNotExist, ValueError, TypeError) as exc:
        raise BloodRequestRejected(
            "request_not_found",
            "Blood request was not found.",
            status_code=404,
        ) from exc


def reserve_blood_request(*, actor, request_id, ip_address=None):
    """Atomically reserve a sufficient, compatible FEFO set for an approved request."""
    _require_staff(actor)
    try:
        with transaction.atomic():
            blood_request = _lock_request(request_id)
            if blood_request.status != BloodRequest.Status.APPROVED:
                raise BloodRequestRejected(
                    "invalid_state_transition",
                    "Only an approved blood request can be reserved.",
                    status_code=409,
                )

            # Lock candidates in a stable order to reduce deadlocks between requests.
            today = blood_bank_today()
            candidates = list(
                BloodUnit.objects.select_for_update()
                .filter(
                    component=blood_request.component,
                    status=BloodUnit.Status.AVAILABLE,
                    expiry_date__gt=today,
                )
                .order_by("pk")
            )
            compatible = select_compatible_units(
                candidates,
                recipient_group=blood_request.patient_blood_group,
                component=blood_request.component,
                donor_group_for=lambda unit: unit.blood_group,
            )
            compatible.sort(
                key=lambda unit: (
                    unit.blood_group != blood_request.patient_blood_group,
                    unit.expiry_date,
                    unit.collected_at,
                    str(unit.pk),
                )
            )

            selected = []
            available_quantity = 0
            for unit in compatible:
                selected.append(unit)
                available_quantity += unit.quantity_units
                if available_quantity >= blood_request.units_needed:
                    break
            if available_quantity < blood_request.units_needed:
                if candidates and not compatible:
                    raise BloodRequestRejected(
                        "incompatible_blood_type",
                        "No available units are compatible with this request.",
                        status_code=422,
                    )
                raise BloodRequestRejected(
                    "insufficient_stock",
                    "There are not enough compatible, unexpired units to reserve this request.",
                    status_code=409,
                    details={"units_needed": ["Insufficient compatible stock."]},
                )

            for unit in selected:
                # Recheck compatibility after acquiring the row lock and before writing.
                if not is_compatible(
                    unit.blood_group,
                    blood_request.patient_blood_group,
                    blood_request.component,
                ):
                    raise BloodRequestRejected(
                        "incompatible_blood_type",
                        "A selected unit is incompatible with this request.",
                        status_code=422,
                    )
                try:
                    transition_blood_unit(
                        actor=actor,
                        unit_id=unit.pk,
                        action=InventoryTransaction.Action.RESERVE,
                        reason=f"Blood request {blood_request.request_id}",
                        ip_address=ip_address,
                        as_of_date=today,
                    )
                except BloodUnitRejected as exc:
                    raise _as_request_rejection(exc) from exc
                unit.status = BloodUnit.Status.RESERVED
                BloodAllocation.objects.create(
                    blood_request=blood_request,
                    blood_unit=unit,
                    status=BloodAllocation.Status.RESERVED,
                )

            blood_request.status = BloodRequest.Status.RESERVED
            blood_request.save(update_fields=("status",))
            record_event(
                action="REQUEST_RESERVED",
                actor=actor,
                entity_type="BLOOD_REQUEST",
                entity_id=blood_request.pk,
                ip_address=ip_address,
            )
            Notification.objects.create(
                recipient=blood_request.requester,
                blood_request=blood_request,
                type=Notification.Type.REQUEST_RESERVED,
            )
            return {
                "request_id": blood_request.request_id,
                "reserved_units": [_unit_response(unit) for unit in selected],
            }
    except IntegrityError as exc:
        raise BloodRequestRejected(
            "unit_unavailable",
            "A selected unit is no longer available for reservation.",
            status_code=409,
        ) from exc


def issue_blood_request(*, actor, request_id, idempotency_key, ip_address=None):
    """Issue all reserved units once, rechecking locked inventory and persisting replay data."""
    _require_staff(actor)
    try:
        with transaction.atomic():
            blood_request = _lock_request(request_id)
            previous = IssueIdempotency.objects.filter(
                blood_request=blood_request,
                key=idempotency_key,
            ).first()
            if previous is not None:
                return previous.response_body
            if blood_request.status != BloodRequest.Status.RESERVED:
                raise BloodRequestRejected(
                    "invalid_state_transition",
                    "Only a reserved blood request can be issued.",
                    status_code=409,
                )

            allocations = list(
                BloodAllocation.objects.select_for_update()
                .filter(
                    blood_request=blood_request,
                    status=BloodAllocation.Status.RESERVED,
                )
                .order_by("blood_unit_id")
            )
            unit_ids = [allocation.blood_unit_id for allocation in allocations]
            locked_units = {
                unit.pk: unit
                for unit in BloodUnit.objects.select_for_update()
                .filter(pk__in=unit_ids)
                .order_by("pk")
            }
            units = [locked_units[unit_id] for unit_id in unit_ids if unit_id in locked_units]
            if (
                len(units) != len(allocations)
                or sum(unit.quantity_units for unit in units) < blood_request.units_needed
            ):
                raise BloodRequestRejected(
                    "unit_unavailable",
                    "The reserved units are no longer available for issue.",
                    status_code=409,
                )

            today = blood_bank_today()
            for unit in units:
                if unit.status != BloodUnit.Status.RESERVED or unit.expiry_date <= today:
                    raise BloodRequestRejected(
                        "unit_unavailable",
                        "A reserved unit is no longer available for issue.",
                        status_code=409,
                    )
                if unit.component != blood_request.component or not is_compatible(
                    unit.blood_group,
                    blood_request.patient_blood_group,
                    blood_request.component,
                ):
                    raise BloodRequestRejected(
                        "incompatible_blood_type",
                        "A reserved unit is incompatible with this request.",
                        status_code=422,
                    )

            for allocation in allocations:
                unit = locked_units[allocation.blood_unit_id]
                try:
                    transition_blood_unit(
                        actor=actor,
                        unit_id=unit.pk,
                        action=InventoryTransaction.Action.ISSUE,
                        reason=f"Blood request {blood_request.request_id}",
                        ip_address=ip_address,
                        as_of_date=today,
                    )
                except BloodUnitRejected as exc:
                    raise _as_request_rejection(exc) from exc
                unit.status = BloodUnit.Status.ISSUED
                allocation.status = BloodAllocation.Status.ISSUED
                allocation.issued_at = timezone.now()
                allocation.save(update_fields=("status", "issued_at"))

            blood_request.status = BloodRequest.Status.FULFILLED
            blood_request.save(update_fields=("status",))
            record_event(
                action="REQUEST_FULFILLED",
                actor=actor,
                entity_type="BLOOD_REQUEST",
                entity_id=blood_request.pk,
                ip_address=ip_address,
            )
            Notification.objects.create(
                recipient=blood_request.requester,
                blood_request=blood_request,
                type=Notification.Type.REQUEST_FULFILLED,
            )
            response_body = {
                "request_id": blood_request.request_id,
                "status": BloodRequest.Status.FULFILLED,
                "issued_units": [_unit_response(unit) for unit in units],
            }
            IssueIdempotency.objects.create(
                blood_request=blood_request,
                key=idempotency_key,
                response_body=response_body,
            )
            return response_body
    except IntegrityError as exc:
        raise BloodRequestRejected(
            "unit_unavailable",
            "A reserved unit is no longer available for issue.",
            status_code=409,
        ) from exc
