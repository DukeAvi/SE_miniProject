"""HTTP handlers for audit APIs."""

from uuid import uuid4

from rest_framework.exceptions import NotFound
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.permissions import RolePermission

from .serializers import AuditEventSerializer, AuditSearchSerializer
from .services import search_events


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


class AuditEventPagination(PageNumberPagination):
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


class AuditEventListView(APIView):
    permission_classes = (IsAuthenticated, RolePermission)
    permission_code = "audit_and_delivery_failures"

    def get_authenticate_header(self, request):
        return "Session"

    def get(self, request):
        allowed = {
            "actor", "action", "from", "to", "entity_type", "entity_id",
            "page", "page_size",
        }
        if set(request.query_params) - allowed:
            return _error("invalid_query", "Unexpected query parameters.")
        query_data = {
            "actor": request.query_params.get("actor"),
            "action": request.query_params.get("action"),
            "from_date": request.query_params.get("from"),
            "to_date": request.query_params.get("to"),
            "entity_type": request.query_params.get("entity_type"),
            "entity_id": request.query_params.get("entity_id"),
            "page": request.query_params.get("page"),
            "page_size": request.query_params.get("page_size"),
        }
        query_data = {key: value for key, value in query_data.items() if value is not None}
        serializer = AuditSearchSerializer(data=query_data)
        serializer.is_valid(raise_exception=True)
        values = serializer.validated_data
        events = search_events(
            actor_id=values.get("actor"),
            action=values.get("action"),
            from_date=values.get("from_date"),
            to_date=values.get("to_date"),
            entity_type=values.get("entity_type"),
            entity_id=values.get("entity_id"),
        )
        paginator = AuditEventPagination()
        try:
            page = paginator.paginate_queryset(events, request, view=self)
        except NotFound:
            return _error(
                "invalid_pagination",
                "Page must be a positive integer within the available results.",
            )
        return paginator.get_paginated_response(
            AuditEventSerializer(page, many=True).data
        )
