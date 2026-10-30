"""TC-Sec-02: disabled accounts cannot bypass view or service authorization."""

from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.urls import URLPattern, URLResolver, get_resolver
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.test import APIRequestFactory

from apps.accounts.services import update_profile
from apps.audit.models import AuditEvent
from apps.core.permissions import ROLE_PERMISSION_MATRIX, RolePermission
from apps.donors.services import (
    AppointmentRejected,
    DonationRejected,
    book_appointment,
    cancel_appointment,
    record_completed_donation,
)
from apps.inventory.models import InventoryTransaction
from apps.inventory.services import BloodUnitRejected, create_verified_blood_unit, transition_blood_unit


pytestmark = pytest.mark.django_db


def test_every_mounted_api_view_declares_a_known_access_policy():
    def mounted(patterns):
        for pattern in patterns:
            if isinstance(pattern, URLResolver):
                yield from mounted(pattern.url_patterns)
            elif isinstance(pattern, URLPattern):
                view = getattr(pattern.callback, "cls", None)
                if view is not None:
                    yield view

    views = set(mounted(get_resolver().url_patterns))
    assert views
    for view in views:
        policies = view.permission_classes
        assert policies and any("permission_classes" in base.__dict__ for base in view.__mro__[:-1])
        assert AllowAny in policies or IsAuthenticated in policies, view.__name__
        if RolePermission in policies:
            assert view.permission_code in ROLE_PERMISSION_MATRIX, view.__name__


@pytest.mark.parametrize("role,code", [("DONOR", "appointments"), ("STAFF", "inventory_write")])
def test_disabled_account_is_denied_even_when_its_role_is_allowed(role, code):
    actor = get_user_model().objects.create_user(
        username=f"disabled-{role.lower()}@example.test",
        email=f"disabled-{role.lower()}@example.test",
        password="Synthetic-Test-Password-532!",
        role=role,
        is_active=False,
    )
    request = APIRequestFactory().get("/api/v1/protected")
    request.user = actor

    assert not RolePermission().has_permission(request, SimpleNamespace(permission_code=code))
    assert AuditEvent.objects.filter(action="ACCESS_DENIED", actor=actor).count() == 1


@pytest.mark.parametrize("role", ["DONOR", "STAFF"])
def test_disabled_actor_is_rejected_by_sensitive_services_before_data_lookup(role):
    actor = get_user_model().objects.create_user(
        username=f"service-{role.lower()}@example.test",
        email=f"service-{role.lower()}@example.test",
        password="Synthetic-Test-Password-532!",
        role=role,
        is_active=False,
    )
    with pytest.raises(PermissionDenied):
        update_profile(user=actor, changes={"first_name": "Changed"})
    if role == "DONOR":
        with pytest.raises(AppointmentRejected) as booking:
            book_appointment(actor=actor, slot_id=uuid4())
        with pytest.raises(AppointmentRejected) as cancellation:
            cancel_appointment(actor=actor, appointment_id=uuid4())
        assert booking.value.code == cancellation.value.code == "forbidden"
    else:
        with pytest.raises(DonationRejected) as donation:
            record_completed_donation(
                actor=actor, donor_id=999, donation_date=date.today(), blood_group="O+",
                component="WHOLE_BLOOD", quantity_units=1,
                screening_weight_kg=Decimal("62.00"),
            )
        with pytest.raises(BloodUnitRejected) as creation:
            create_verified_blood_unit(
                actor=actor, donation_id=uuid4(), unit_code="SYNTHETIC-UNIT",
                blood_group="O+", component="RBC", collected_at=None,
                expiry_date=date.today(), quantity_units=1,
            )
        with pytest.raises(BloodUnitRejected) as transition:
            transition_blood_unit(
                actor=actor, unit_id=uuid4(), action=InventoryTransaction.Action.DISCARD,
                reason="Test",
            )
        assert donation.value.code == "forbidden"
        assert creation.value.code == transition.value.code == "forbidden"
    assert AuditEvent.objects.count() == 0
