"""Staff-only donor selection and initial profile verification endpoints."""

from uuid import uuid4

from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.permissions import RolePermission

from .onboarding import DonorOnboardingRejected, create_donor_profile, find_donors
from .onboarding_serializers import (
    DonorLookupQuerySerializer,
    DonorLookupSerializer,
    DonorProfileCreateSerializer,
    DonorProfileResultSerializer,
)


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


class StaffDonorLookupView(APIView):
    permission_classes = (IsAuthenticated, RolePermission)
    permission_code = "donor_detail"

    def get(self, request):
        if set(request.query_params) != {"q"}:
            return _error("invalid_query", "Provide only the q search parameter.")
        serializer = DonorLookupQuerySerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        donors = find_donors(query=serializer.validated_data["q"])
        return Response({"results": DonorLookupSerializer(donors, many=True).data})


@method_decorator(csrf_protect, name="dispatch")
class StaffDonorProfileCreateView(APIView):
    permission_classes = (IsAuthenticated, RolePermission)
    permission_code = "donor_detail"

    def post(self, request):
        if request.query_params:
            return _error("invalid_query", "Unexpected query parameters.")
        serializer = DonorProfileCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            profile = create_donor_profile(
                **serializer.validated_data,
                actor=request.user,
                ip_address=request.META.get("REMOTE_ADDR"),
            )
        except DonorOnboardingRejected as exc:
            return _error(exc.code, exc.message, status_code=exc.status_code)
        return Response(
            DonorProfileResultSerializer(profile).data,
            status=201,
        )
