"""HTTP handlers for inventory APIs."""

from uuid import uuid4

from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.permissions import RolePermission

from .models import InventoryTransaction
from .serializers import BloodUnitCreateSerializer, BloodUnitSerializer, BloodUnitTransitionSerializer
from .services import BloodUnitRejected, create_verified_blood_unit, transition_blood_unit


def _error(code, message, details=None, status_code=400):
    return Response({"error": {"code": code, "message": message, "details": details or {}, "correlation_id": str(uuid4())}}, status=status_code)


@method_decorator(csrf_protect, name="dispatch")
class BloodUnitCreateView(APIView):
    permission_classes = (IsAuthenticated, RolePermission)
    permission_code = "inventory_write"

    def get_authenticate_header(self, request):
        return "Session"

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
