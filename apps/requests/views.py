"""HTTP handlers for blood request APIs."""

from uuid import uuid4

from django.core.paginator import EmptyPage, Paginator
from django.http import Http404
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.permissions import RolePermission
from apps.audit.models import AuditEvent
from apps.audit.services import record_event

from .serializers import (
    BloodRequestCreateSerializer,
    BloodRequestDecisionSerializer,
    BloodRequestDetailSerializer,
    BloodRequestSerializer,
)
from .models import BloodRequest
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

    def get_permissions(self):
        self.permission_code = (
            "request_read" if self.request.method == "GET" else "blood_request_create"
        )
        return super().get_permissions()

    def get(self, request):
        if set(request.query_params) - {"page", "page_size"}:
            return _error("invalid_query", "Unsupported query parameters.")
        try:
            page = _positive_query_int(request.query_params.get("page", "1"), "page")
            page_size = _positive_query_int(
                request.query_params.get("page_size", "20"), "page_size"
            )
        except ValueError as exc:
            return _error("invalid_query", str(exc))
        if page_size > 100:
            return _error("invalid_query", "page_size must be between 1 and 100.")

        queryset = BloodRequest.objects.all()
        if request.user.role == "RECIPIENT":
            queryset = queryset.filter(requester=request.user)
        elif request.user.role != "STAFF":
            return _error("forbidden", "This role cannot view blood requests.", status_code=403)
        queryset = queryset.order_by("-created_at", "request_id")
        paginator = Paginator(queryset, page_size)
        try:
            page_obj = paginator.page(page)
        except EmptyPage:
            page_obj = None
        results = page_obj.object_list if page_obj else []
        return Response({
            "count": paginator.count,
            "page": page,
            "page_size": page_size,
            "results": BloodRequestSerializer(results, many=True).data,
        })

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


@method_decorator(csrf_protect, name="dispatch")
class BloodRequestDetailView(APIView):
    permission_classes = (IsAuthenticated, RolePermission)
    permission_code = "request_read"

    def get_authenticate_header(self, request):
        return "Session"

    def get(self, request, request_id):
        if request.query_params:
            return _error("invalid_query", "Unexpected query parameters.")
        queryset = BloodRequest.objects.all()
        if request.user.role == "RECIPIENT":
            queryset = queryset.filter(requester=request.user)
        try:
            blood_request = queryset.get(request_id=request_id)
        except BloodRequest.DoesNotExist as exc:
            if request.user.role == "RECIPIENT":
                record_event(
                    action="ACCESS_DENIED",
                    actor=request.user,
                    outcome="FAILURE",
                    ip_address=request.META.get("REMOTE_ADDR"),
                )
            raise Http404 from exc

        action_status = {
            "REQUEST_SUBMITTED": "PENDING",
            "REQUEST_APPROVED": "APPROVED",
            "REQUEST_REJECTED": "REJECTED",
            "REQUEST_HELD": "ON_HOLD",
            "REQUEST_RESERVED": "RESERVED",
            "REQUEST_FULFILLED": "FULFILLED",
        }
        events = AuditEvent.objects.filter(
            entity_type="BLOOD_REQUEST",
            entity_id=str(blood_request.pk),
            action__in=action_status,
        ).order_by("occurred_at", "id")
        history = [{
            "status": action_status[event.action],
            "occurred_at": event.occurred_at,
        } for event in events]
        return Response(BloodRequestDetailSerializer(
            blood_request,
            context={"status_history": {blood_request.pk: history}},
        ).data)


def _positive_query_int(value, name):
    if not isinstance(value, str) or not value.isdecimal() or int(value) < 1:
        raise ValueError(f"{name} must be a positive integer.")
    return int(value)
