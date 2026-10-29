"""HTTP handlers for donor APIs."""

from uuid import uuid4
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from django.conf import settings
from django.db.models import Count, Q
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.permissions import RolePermission

from .models import Appointment, Donation, DonationSlot, DonorProfile
from .serializers import (
    AppointmentCreateSerializer,
    AppointmentSerializer,
    DonationCreateSerializer,
    DonationSerializer,
    DonationSlotSerializer,
)
from .services import (
    AppointmentRejected,
    DonationRejected,
    book_appointment,
    cancel_appointment,
    record_completed_donation,
)


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


class AppointmentPagination(PageNumberPagination):
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


class DonationSlotListView(APIView):
    permission_classes = (IsAuthenticated, RolePermission)
    permission_code = "donation_slot_list"

    def get_authenticate_header(self, request):
        return "Session"

    def get(self, request):
        allowed = {"date", "page", "page_size"}
        if set(request.query_params) - allowed or "date" not in request.query_params:
            return _error("invalid_query", "A date and only supported pagination parameters are required.")
        try:
            requested_date = datetime.strptime(request.query_params["date"], "%Y-%m-%d").date()
        except ValueError:
            return _error("validation_error", "Date must use YYYY-MM-DD.")
        zone = ZoneInfo(settings.BLOOD_BANK_TIME_ZONE)
        local_start = datetime.combine(requested_date, time.min, tzinfo=zone)
        local_end = local_start + timedelta(days=1)
        slots = DonationSlot.objects.filter(
            starts_at__gte=local_start,
            starts_at__lt=local_end,
        ).annotate(
            active_bookings=Count("appointments", filter=Q(appointments__status=Appointment.Status.BOOKED)),
        ).order_by("starts_at", "id")
        paginator = AppointmentPagination()
        page = paginator.paginate_queryset(slots, request, view=self)
        return paginator.get_paginated_response(DonationSlotSerializer(page, many=True).data)


@method_decorator(csrf_protect, name="dispatch")
class MyAppointmentListCreateView(APIView):
    permission_classes = (IsAuthenticated, RolePermission)
    permission_code = "appointments"

    def get_authenticate_header(self, request):
        return "Session"

    def post(self, request):
        if request.query_params:
            return _error("invalid_query", "Unexpected query parameters.")
        serializer = AppointmentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            appointment = book_appointment(
                actor=request.user,
                slot_id=serializer.validated_data["slot_id"],
                ip_address=request.META.get("REMOTE_ADDR"),
            )
        except AppointmentRejected as exc:
            return _error(exc.code, exc.message, exc.details, exc.status_code)
        return Response(AppointmentSerializer(appointment).data, status=status.HTTP_201_CREATED)

    def get(self, request):
        allowed = {"page", "page_size"}
        if set(request.query_params) - allowed:
            return _error("invalid_query", "Unexpected query parameters.")
        try:
            profile = DonorProfile.objects.get(user=request.user)
        except DonorProfile.DoesNotExist:
            return _error("donor_profile_not_found", "Donor profile was not found.", status_code=404)
        appointments = Appointment.objects.filter(donor=profile).select_related("slot")
        paginator = AppointmentPagination()
        page = paginator.paginate_queryset(appointments, request, view=self)
        return paginator.get_paginated_response(AppointmentSerializer(page, many=True).data)


@method_decorator(csrf_protect, name="dispatch")
class AppointmentCancelView(APIView):
    permission_classes = (IsAuthenticated, RolePermission)
    permission_code = "appointments"

    def get_authenticate_header(self, request):
        return "Session"

    def post(self, request, appointment_id):
        if request.query_params or request.data:
            return _error("invalid_request", "Cancellation does not accept request fields.")
        try:
            appointment = cancel_appointment(
                actor=request.user,
                appointment_id=appointment_id,
                ip_address=request.META.get("REMOTE_ADDR"),
            )
        except AppointmentRejected as exc:
            return _error(exc.code, exc.message, exc.details, exc.status_code)
        return Response(AppointmentSerializer(appointment).data)
