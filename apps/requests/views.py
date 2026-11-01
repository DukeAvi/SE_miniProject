"""HTTP handlers for blood request APIs."""

from uuid import uuid4

from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.permissions import RolePermission

from .serializers import (
    BloodRequestCreateSerializer,
    BloodRequestDecisionSerializer,
    BloodRequestSerializer,
)
from .services import BloodRequestRejected, decide_blood_request, submit_blood_request


def _error(code, message, details=None, status_code=400):
    return Response(
        {
            "error": {
                "code": code,
                "message": message,
                "details": details or {},
                "correlation_id": str(uuid4()),
            }
        },
        status=status_code,
    )


@method_decorator(csrf_protect, name="dispatch")
class BloodRequestCollectionView(APIView):
    permission_classes = (IsAuthenticated, RolePermission)
    permission_code = "blood_request_create"

    def get_authenticate_header(self, request):
        return "Session"

    def post(self, request):
        if request.query_params:
            return _error("invalid_query", "Unexpected query parameters.")
        serializer = BloodRequestCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            blood_request = submit_blood_request(
                **serializer.validated_data,
                actor=request.user,
                ip_address=request.META.get("REMOTE_ADDR"),
            )
        except BloodRequestRejected as exc:
            return _error(exc.code, exc.message, exc.details, exc.status_code)
        return Response(
            BloodRequestSerializer(blood_request).data,
            status=status.HTTP_201_CREATED,
        )


@method_decorator(csrf_protect, name="dispatch")
class BloodRequestDecisionView(APIView):
    permission_classes = (IsAuthenticated, RolePermission)
    permission_code = "request_review"

    def get_authenticate_header(self, request):
        return "Session"

    def post(self, request, request_id):
        if request.query_params:
            return _error("invalid_query", "Unexpected query parameters.")
        serializer = BloodRequestDecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            blood_request = decide_blood_request(
                actor=request.user,
                request_id=request_id,
                decision=serializer.validated_data["decision"],
                reason=serializer.validated_data.get("reason", ""),
                ip_address=request.META.get("REMOTE_ADDR"),
            )
        except BloodRequestRejected as exc:
            return _error(exc.code, exc.message, exc.details, exc.status_code)
        return Response(BloodRequestSerializer(blood_request).data)
