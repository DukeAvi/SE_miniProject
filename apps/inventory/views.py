"""HTTP handlers for inventory APIs."""

from uuid import uuid4
from zoneinfo import ZoneInfo

from django.conf import settings
from django.db.models import Count, Min
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.permissions import RolePermission

from .models import BloodUnit, InventoryTransaction
from .serializers import BloodUnitCreateSerializer, BloodUnitSerializer, BloodUnitTransitionSerializer
from .services import BloodUnitRejected, create_verified_blood_unit, transition_blood_unit


def _error(code, message, details=None, status_code=400):
    return Response({"error": {"code": code, "message": message, "details": details or {}, "correlation_id": str(uuid4())}}, status=status_code)


def blood_bank_today():
    return timezone.localdate(timezone=ZoneInfo(settings.BLOOD_BANK_TIME_ZONE))


class BloodUnitPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100

    def get_paginated_response(self, data):
        return Response({
            "count": self.page.paginator.count,
            "page": self.page.number,
            "page_size": self.get_page_size(self.request),
            "results": data,
        })


class BloodUnitListView(APIView):
    permission_classes = (IsAuthenticated, RolePermission)
    permission_code = "inventory_search"

    def get_authenticate_header(self, request):
        return "Session"

    def get(self, request):
        allowed = {"blood_group", "component", "status", "page", "page_size"}
        if set(request.query_params) - allowed:
            return _error("invalid_query", "Unexpected query parameters.")
        filters = {
            "status": request.query_params.get("status", BloodUnit.Status.AVAILABLE),
            "expiry_date__gt": blood_bank_today(),
        }
        errors = {}
        valid_groups = tuple(BloodUnitCreateSerializer().fields["blood_group"].choices)
        for name, choices in (
            ("blood_group", valid_groups),
            ("component", tuple(BloodUnit.Component.values)),
            ("status", tuple(BloodUnit.Status.values)),
        ):
            value = request.query_params.get(name)
            if value is not None:
                if value not in choices:
                    errors[name] = ["Invalid choice."]
                else:
                    filters[name] = value
        if errors:
            return _error("validation_error", "The request could not be processed.", errors)

        records = BloodUnit.objects.filter(**filters).order_by("expiry_date", "created_at", "id")
        paginator = BloodUnitPagination()
        try:
            page = paginator.paginate_queryset(records, request, view=self)
        except NotFound:
            return _error("invalid_pagination", "Page must be a positive integer within the available results.")
        return paginator.get_paginated_response(BloodUnitSerializer(page, many=True).data)


class BloodAvailabilityView(APIView):
    permission_classes = (IsAuthenticated, RolePermission)
    permission_code = "availability_aggregate"

    def get_authenticate_header(self, request):
        return "Session"

    def get(self, request):
        allowed = {"blood_group", "component"}
        if set(request.query_params) - allowed:
            return _error("invalid_query", "Unexpected query parameters.")
        errors = {}
        blood_group = request.query_params.get("blood_group")
        component = request.query_params.get("component")
        valid_groups = tuple(BloodUnitCreateSerializer().fields["blood_group"].choices)
        if blood_group is None:
            errors["blood_group"] = ["This field is required."]
        elif blood_group not in valid_groups:
            errors["blood_group"] = ["Invalid choice."]
        if component is None:
            errors["component"] = ["This field is required."]
        elif component not in BloodUnit.Component.values:
            errors["component"] = ["Invalid choice."]
        if errors:
            return _error("validation_error", "The request could not be processed.", errors)

        result = BloodUnit.objects.filter(
            blood_group=blood_group,
            component=component,
            status=BloodUnit.Status.AVAILABLE,
            expiry_date__gt=blood_bank_today(),
        ).aggregate(available_units=Count("pk"), nearest_expiry=Min("expiry_date"))
        return Response({
            "blood_group": blood_group,
            "component": component,
            "available_units": result["available_units"],
            "nearest_expiry": result["nearest_expiry"],
        })


@method_decorator(csrf_protect, name="dispatch")
class BloodUnitCollectionView(BloodUnitListView):
    """Expose staff collection and search under the inventory collection URL."""

    permission_code = "inventory_write"

    def post(self, request):
        if request.query_params:
            return _error("invalid_query", "Unexpected query parameters.")
        serializer = BloodUnitCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            unit = create_verified_blood_unit(
                **serializer.validated_data,
                actor=request.user,
                ip_address=request.META.get("REMOTE_ADDR"),
            )
        except BloodUnitRejected as exc:
            return _error(exc.code, exc.message, exc.details, exc.status_code)
        return Response(BloodUnitSerializer(unit).data, status=status.HTTP_201_CREATED)


@method_decorator(csrf_protect, name="dispatch")
class BloodUnitTransitionView(APIView):
    permission_classes = (IsAuthenticated, RolePermission)
    permission_code = "inventory_write"
    action = None

    def get_authenticate_header(self, request):
        return "Session"

    def post(self, request, unit_id):
        if request.query_params:
            return _error("invalid_query", "Unexpected query parameters.")
        serializer = BloodUnitTransitionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            unit = transition_blood_unit(
                actor=request.user,
                unit_id=unit_id,
                action=self.action,
                reason=serializer.validated_data["reason"],
                ip_address=request.META.get("REMOTE_ADDR"),
            )
        except BloodUnitRejected as exc:
            return _error(exc.code, exc.message, exc.details, exc.status_code)
        return Response(BloodUnitSerializer(unit).data)


class BloodUnitDiscardView(BloodUnitTransitionView):
    action = InventoryTransaction.Action.DISCARD


class BloodUnitReturnView(BloodUnitTransitionView):
    action = InventoryTransaction.Action.RETURN
