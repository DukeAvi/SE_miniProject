"""HTTP handlers for notification APIs."""

from uuid import uuid4

from django.core.paginator import EmptyPage, Paginator
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.permissions import RolePermission

from .models import Notification
from .serializers import NotificationFailureSerializer, NotificationSerializer


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


def _page(request):
    if set(request.query_params) - {"page", "page_size"}:
        return None, _error("invalid_query", "Unsupported query parameters.")
    try:
        page = _positive_int(request.query_params.get("page", "1"), "page")
        page_size = _positive_int(request.query_params.get("page_size", "20"), "page_size")
    except ValueError as exc:
        return None, _error("invalid_query", str(exc))
    if page_size > 100:
        return None, _error("invalid_query", "page_size must be between 1 and 100.")
    return (page, page_size), None


def _positive_int(value, field):
    if not isinstance(value, str) or not value.isdecimal() or int(value) < 1:
        raise ValueError(f"{field} must be a positive integer.")
    return int(value)


def _page_response(queryset, page, page_size, serializer_class):
    paginator = Paginator(queryset, page_size)
    try:
        page_obj = paginator.page(page)
    except EmptyPage:
        page_obj = None
    return Response({
        "count": paginator.count,
        "page": page,
        "page_size": page_size,
        "results": serializer_class(
            page_obj.object_list if page_obj else [], many=True
        ).data,
    })


@method_decorator(csrf_protect, name="dispatch")
class NotificationCollectionView(APIView):
    permission_classes = (IsAuthenticated, RolePermission)
    permission_code = "own_notifications"

    def get_authenticate_header(self, request):
        return "Session"

    def get(self, request):
        pagination, error = _page(request)
        if error:
            return error
        page, page_size = pagination
        notifications = Notification.objects.filter(recipient=request.user).select_related(
            "stock_alert__threshold"
        ).order_by("-created_at", "-id")
        return _page_response(notifications, page, page_size, NotificationSerializer)


@method_decorator(csrf_protect, name="dispatch")
class NotificationFailureCollectionView(APIView):
    permission_classes = (IsAuthenticated, RolePermission)
    permission_code = "audit_and_delivery_failures"

    def get_authenticate_header(self, request):
        return "Session"

    def get(self, request):
        pagination, error = _page(request)
        if error:
            return error
        page, page_size = pagination
        failures = Notification.objects.filter(
            status=Notification.Status.FAILED
        ).order_by("-created_at", "-id")
        return _page_response(
            failures, page, page_size, NotificationFailureSerializer
        )
