"""HTTP handlers for account APIs."""

from uuid import uuid4

from django.conf import settings
from django.contrib.auth import logout as auth_logout
from django.middleware.csrf import get_token
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import LoginSerializer, RegistrationSerializer, UserPublicSerializer
from .services import (
    DASHBOARD_PATHS,
    login_account,
)


@method_decorator(csrf_protect, name="dispatch")
class RegistrationView(generics.CreateAPIView):
    serializer_class = RegistrationSerializer
    permission_classes = (AllowAny,)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        headers = self.get_success_headers(serializer.data)
        return Response(
            UserPublicSerializer(user).data,
            status=status.HTTP_201_CREATED,
            headers=headers,
        )


@method_decorator(ensure_csrf_cookie, name="dispatch")
class CsrfTokenView(APIView):
    authentication_classes = ()
    permission_classes = (AllowAny,)

    def get(self, request):
        return Response({"csrfToken": get_token(request)})


def _authentication_error(
    *,
    code: str,
    message: str,
    status_code: int,
    retry_after: int | None = None,
):
    response = Response(
        {
            "error": {
                "code": code,
                "message": message,
                "details": {},
                "correlation_id": str(uuid4()),
            }
        },
        status=status_code,
    )
    if retry_after is not None:
        response["Retry-After"] = str(retry_after)
    return response


@method_decorator(csrf_protect, name="dispatch")
class LoginView(APIView):
    permission_classes = (AllowAny,)

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]
        password = serializer.validated_data["password"]
        ip_address = request.META.get("REMOTE_ADDR")

        user, retry_after = login_account(
            request=request,
            email=email,
            password=password,
            ip_address=ip_address,
        )
        if retry_after is not None:
            return _authentication_error(
                code="too_many_attempts",
                message="Too many login attempts. Try again later.",
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                retry_after=retry_after,
            )

        if user is not None:
            return Response(
                {
                    "user": {
                        "id": user.pk,
                        "name": user.get_full_name(),
                        "role": user.role,
                    },
                    "redirect": DASHBOARD_PATHS[user.role],
                    "session_expires_in": settings.SESSION_COOKIE_AGE,
                }
            )

        return _authentication_error(
            code="invalid_credentials",
            message="Email or password is incorrect.",
            status_code=status.HTTP_401_UNAUTHORIZED,
        )


@method_decorator(csrf_protect, name="dispatch")
class LogoutView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        auth_logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)
