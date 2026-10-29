"""Deny-by-default role policies aligned with SAD Section 3.9.2."""

from rest_framework.permissions import BasePermission

from apps.audit.services import record_event


ROLE_PERMISSION_MATRIX = {
    "self_profile": frozenset({"DONOR", "RECIPIENT", "STAFF", "ADMIN"}),
    "appointments": frozenset({"DONOR"}),
    "donation_slot_list": frozenset({"DONOR", "STAFF"}),
    "own_donation_history": frozenset({"DONOR"}),
    "donor_detail": frozenset({"STAFF"}),
    "donation_record": frozenset({"STAFF"}),
    "inventory_write": frozenset({"STAFF"}),
    "inventory_search": frozenset({"STAFF"}),
    "availability_aggregate": frozenset({"RECIPIENT"}),
    "availability_units": frozenset({"STAFF"}),
    "blood_request_create": frozenset({"RECIPIENT"}),
    "own_requests": frozenset({"RECIPIENT"}),
    "all_requests": frozenset({"STAFF"}),
    "request_review": frozenset({"STAFF"}),
    "unit_fulfillment": frozenset({"STAFF"}),
    "own_notifications": frozenset({"DONOR", "RECIPIENT", "STAFF", "ADMIN"}),
    "reports": frozenset({"STAFF", "ADMIN"}),
    "stock_thresholds": frozenset({"ADMIN"}),
    "staff_accounts": frozenset({"ADMIN"}),
    "audit_and_delivery_failures": frozenset({"ADMIN"}),
}


def _record_denial(request) -> None:
    user = getattr(request, "user", None)
    actor = user if user is not None and user.is_authenticated else None
    record_event(
        action="ACCESS_DENIED",
        actor=actor,
        ip_address=request.META.get("REMOTE_ADDR"),
    )


class DenyByDefaultPermission(BasePermission):
    """Reject API views unless they declare an explicit permission policy."""

    def has_permission(self, request, view):
        _record_denial(request)
        return False


class RolePermission(BasePermission):
    """Authorize a view using its SAD operation code; unknown codes deny."""

    def has_permission(self, request, view):
        permission_code = getattr(view, "permission_code", None)
        allowed_roles = ROLE_PERMISSION_MATRIX.get(permission_code, frozenset())
        user = request.user
        allowed = bool(
            user.is_authenticated
            and getattr(user, "role", None) in allowed_roles
        )
        if not allowed:
            _record_denial(request)
        return allowed
