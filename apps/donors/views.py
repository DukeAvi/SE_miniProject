"""HTTP handlers for donor APIs."""

from uuid import uuid4

from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.permissions import RolePermission

from .models import Donation, DonorProfile
from .serializers import DonationCreateSerializer, DonationSerializer
from .services import DonationRejected, record_completed_donation


def _error(code, message, details=None, status_code=400):
    return Response({"error": {"code": code, "message": message, "details": details or {}, "correlation_id": str(uuid4())}}, status=status_code)


@method_decorator(csrf_protect, name="dispatch")
class DonationRecordView(APIView):
    permission_classes = (IsAuthenticated, RolePermission)
    permission_code = "donation_record"

    def get_authenticate_header(self, request):
        return "Session"

    def post(self, request):
        if request.query_params:
            return _error("invalid_query", "Unexpected query parameters.")
        serializer = DonationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        donation_data = dict(serializer.validated_data)
        donation_data.pop("status")
        try:
            donation = record_completed_donation(
                **donation_data,
                actor=request.user,
                ip_address=request.META.get("REMOTE_ADDR"),
            )
        except DonationRejected as exc:
            code_status = 404 if exc.code == "donor_not_found" else (403 if exc.code == "forbidden" else 422)
            return _error(exc.code, exc.message, exc.details, code_status)
        return Response(DonationSerializer(donation).data, status=status.HTTP_201_CREATED)


class DonationHistoryPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = None
    max_page_size = 100

    def get_paginated_response(self, data):
        return Response({
            "count": self.page.paginator.count,
            "page": self.page.number,
            "page_size": self.page_size,
            "results": data,
        })


class MyDonationHistoryView(APIView):
    permission_classes = (IsAuthenticated, RolePermission)
    permission_code = "own_donation_history"

    def get(self, request):
        if request.query_params.keys() - {"page"}:
            return _error("invalid_query", "Unexpected query parameters.")
        try:
            profile = DonorProfile.objects.get(user=request.user)
        except DonorProfile.DoesNotExist as exc:
            raise NotFound("Donor profile was not found.") from exc
        records = Donation.objects.filter(donor=profile).select_related("donor")
        paginator = DonationHistoryPagination()
        page = paginator.paginate_queryset(records, request, view=self)
        return paginator.get_paginated_response(DonationSerializer(page, many=True).data)
