from types import SimpleNamespace

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.http import Http404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.test import APIRequestFactory, force_authenticate
from rest_framework.views import APIView

from apps.audit.models import AuditEvent
from apps.core.ownership import get_owned_object_or_404
from apps.core.permissions import (
    DenyByDefaultPermission,
    ROLE_PERMISSION_MATRIX,
    RolePermission,
)


pytestmark = pytest.mark.django_db

EXPECTED_MATRIX = {
    "self_profile": {"DONOR", "RECIPIENT", "STAFF", "ADMIN"},
    "appointments": {"DONOR"},
    "own_donation_history": {"DONOR"},
    "donor_detail": {"STAFF"},
    "donation_record": {"STAFF"},
    "inventory_write": {"STAFF"},
    "inventory_search": {"STAFF"},
    "availability_aggregate": {"RECIPIENT"},
    "availability_units": {"STAFF"},
    "blood_request_create": {"RECIPIENT"},
    "own_requests": {"RECIPIENT"},
    "all_requests": {"STAFF"},
    "request_review": {"STAFF"},
    "unit_fulfillment": {"STAFF"},
    "own_notifications": {"DONOR", "RECIPIENT", "STAFF", "ADMIN"},
    "reports": {"STAFF", "ADMIN"},
    "stock_thresholds": {"ADMIN"},
    "staff_accounts": {"ADMIN"},
    "audit_and_delivery_failures": {"ADMIN"},
}
ROLES = ("DONOR", "RECIPIENT", "STAFF", "ADMIN")


def user_for(role, index):
    email = f"{role.lower()}{index}@example.test"
    return get_user_model().objects.create_user(
        username=email,
        email=email,
        password="Safe-Long-Password-532!",
        first_name="Test",
        last_name=role.title(),
        phone=f"+1202555{index:04d}",
        role=role,
    )


def test_role_matrix_matches_sad_and_is_enforced_for_every_role_cell():
    assert {key: set(value) for key, value in ROLE_PERMISSION_MATRIX.items()} == EXPECTED_MATRIX
    factory = APIRequestFactory()
    permission = RolePermission()
    users = {role: user_for(role, index + 1) for index, role in enumerate(ROLES)}
    expected_denials = 0

    for permission_code, allowed_roles in EXPECTED_MATRIX.items():
        view = SimpleNamespace(permission_code=permission_code)
        for role, user in users.items():
            request = factory.get("/api/v1/protected")
            request.user = user
            permitted = permission.has_permission(request, view)
            assert permitted is (role in allowed_roles), (permission_code, role)
            expected_denials += role not in allowed_roles

    assert AuditEvent.objects.filter(action="ACCESS_DENIED").count() == expected_denials


def test_unconfigured_and_unknown_permission_codes_deny_and_audit():
    user = user_for("DONOR", 10)
    request = APIRequestFactory().get("/api/v1/unconfigured")
    request.user = user

    assert not DenyByDefaultPermission().has_permission(request, SimpleNamespace())
    assert not RolePermission().has_permission(
        request,
        SimpleNamespace(permission_code="made_up_operation"),
    )
    assert AuditEvent.objects.filter(action="ACCESS_DENIED", actor=user).count() == 2


def test_staff_or_superuser_flags_do_not_override_role_matrix():
    donor = user_for("DONOR", 11)
    donor.is_staff = True
    donor.is_superuser = True
    request = APIRequestFactory().get("/api/v1/admin/stock-thresholds")
    request.user = donor

    assert not RolePermission().has_permission(
        request,
        SimpleNamespace(permission_code="stock_thresholds"),
    )
    assert AuditEvent.objects.filter(action="ACCESS_DENIED", actor=donor).exists()


class OwnedAuditEventView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request, event_id):
        event = get_owned_object_or_404(
            AuditEvent.objects.all(),
            request=request,
            lookup={"pk": event_id},
            owner_field="actor",
        )
        return Response({"id": event.pk, "action": event.action})


class UnconfiguredAPIView(APIView):
    def get(self, request):
        return Response({"status": "should not be reachable"})


def test_api_view_without_explicit_permission_is_denied_by_default():
    user = user_for("DONOR", 14)
    request = APIRequestFactory().get("/api/v1/unconfigured")
    force_authenticate(request, user=user)

    response = UnconfiguredAPIView.as_view()(request)

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert AuditEvent.objects.filter(action="ACCESS_DENIED", actor=user).count() == 1


def test_owned_object_helper_returns_same_404_for_foreign_and_missing_records():
    owner = user_for("DONOR", 12)
    other = user_for("RECIPIENT", 13)
    event = AuditEvent.objects.create(action="LOGIN_SUCCESS", actor=owner)
    factory = APIRequestFactory()
    view = OwnedAuditEventView.as_view()

    own_request = factory.get(f"/owned/{event.pk}")
    force_authenticate(own_request, user=owner)
    own_response = view(own_request, event_id=event.pk)
    assert own_response.status_code == status.HTTP_200_OK

    foreign_request = factory.get(f"/owned/{event.pk}")
    force_authenticate(foreign_request, user=other)
    foreign_response = view(foreign_request, event_id=event.pk)

    missing_request = factory.get("/owned/999999")
    force_authenticate(missing_request, user=other)
    missing_response = view(missing_request, event_id=999999)

    assert foreign_response.status_code == missing_response.status_code == status.HTTP_404_NOT_FOUND
    assert foreign_response.data == missing_response.data
    assert AuditEvent.objects.filter(action="ACCESS_DENIED", actor=other).count() == 2


def test_anonymous_owned_object_lookup_is_not_found():
    request = APIRequestFactory().get("/owned/1")
    request.user = AnonymousUser()

    with pytest.raises(Http404):
        get_owned_object_or_404(
            AuditEvent.objects.all(),
            request=request,
            lookup={"pk": 1},
            owner_field="actor",
        )
