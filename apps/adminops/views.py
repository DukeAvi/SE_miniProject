"""HTTP handlers for administration APIs."""

from uuid import uuid4

from django.contrib.auth import get_user_model
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import AccountRole
from apps.core.permissions import RolePermission

from .serializers import (
    ManagedUserCreateSerializer,
    ManagedUserPatchSerializer,
    ManagedUserSerializer,
)
from .services import ManagedUserRejected, create_managed_user, update_managed_user


User = get_user_model()


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


class ManagedUserPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100

    def get_paginated_response(self, data):
        return Response(
            {
                "count": self.page.paginator.count,
                "page": self.page.number,
                "page_size": self.get_page_size(self.request),
                "results": data,
            }
        )


@method_decorator(csrf_protect, name="dispatch")
class ManagedUserCollectionView(APIView):
    permission_classes = (IsAuthenticated, RolePermission)
    permission_code = "staff_accounts"

    def get_authenticate_header(self, request):
        return "Session"

    def get(self, request):
        if set(request.query_params) - {"page", "page_size"}:
            return _error("invalid_query", "Unexpected query parameters.")
        users = User.objects.filter(
            role__in=(AccountRole.STAFF, AccountRole.ADMIN)
        ).order_by("email", "pk")
        paginator = ManagedUserPagination()
        try:
            page = paginator.paginate_queryset(users, request, view=self)
        except NotFound:
            return _error(
                "invalid_pagination",
                "Page must be a positive integer within the available results.",
            )
        return paginator.get_paginated_response(
            ManagedUserSerializer(page, many=True).data
        )

    def post(self, request):
        if request.query_params:
            return _error("invalid_query", "Unexpected query parameters.")
        serializer = ManagedUserCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            user = create_managed_user(
                **serializer.validated_data,
                actor=request.user,
                ip_address=request.META.get("REMOTE_ADDR"),
            )
        except ManagedUserRejected as exc:
            return _error(exc.code, exc.message, exc.details, exc.status_code)
        return Response(
            ManagedUserSerializer(user).data,
            status=status.HTTP_201_CREATED,
        )


@method_decorator(csrf_protect, name="dispatch")
class ManagedUserDetailView(APIView):
    permission_classes = (IsAuthenticated, RolePermission)
    permission_code = "staff_accounts"

    def get_authenticate_header(self, request):
        return "Session"

    def patch(self, request, user_id):
        if request.query_params:
            return _error("invalid_query", "Unexpected query parameters.")
        serializer = ManagedUserPatchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            user = update_managed_user(
                actor=request.user,
                user_id=user_id,
                changes=serializer.validated_data,
                ip_address=request.META.get("REMOTE_ADDR"),
            )
        except ManagedUserRejected as exc:
            return _error(exc.code, exc.message, exc.details, exc.status_code)
        return Response(ManagedUserSerializer(user).data)
