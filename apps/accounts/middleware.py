"""Enforce idle and absolute authentication session expiry."""

from uuid import uuid4

from django.conf import settings
from django.contrib.auth import logout
from django.http import JsonResponse
from django.utils import timezone

from apps.audit.services import record_event


class SessionExpiryMiddleware:
    """Apply sliding idle and absolute limits to authenticated API sessions."""

    PUBLIC_API_PATHS = {
        "/api/v1/auth/login",
        "/api/v1/auth/register",
        "/api/v1/auth/csrf",
    }

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = request.user
        if user.is_authenticated:
            started_at = request.session.get("auth_started_at")
            if started_at is None:
                started_at = timezone.now().timestamp()
                request.session["auth_started_at"] = started_at
            elapsed = timezone.now().timestamp() - float(started_at)
            if elapsed >= settings.SESSION_ABSOLUTE_TIMEOUT_SECONDS:
                self._record_expiry(request, user)
                logout(request)
                return self._expired_response()
        elif (
            request.path.startswith("/api/")
            and request.path not in self.PUBLIC_API_PATHS
            and request.COOKIES.get(settings.SESSION_COOKIE_NAME)
        ):
            # Django's database session backend treats an expired session as
            # empty. Cookie presence distinguishes that case without reading
            # or logging its value.
            self._record_expiry(request)
            return self._expired_response()

        return self.get_response(request)

    @staticmethod
    def _record_expiry(request, actor=None):
        record_event(
            action="SESSION_EXPIRED",
            actor=actor,
            ip_address=request.META.get("REMOTE_ADDR"),
        )

    @staticmethod
    def _expired_response():
        response = JsonResponse(
            {
                "error": {
                    "code": "session_expired",
                    "message": "Your session expired. Please sign in again.",
                    "details": {},
                    "correlation_id": str(uuid4()),
                }
            },
            status=401,
        )
        response.delete_cookie(
            settings.SESSION_COOKIE_NAME,
            path=settings.SESSION_COOKIE_PATH,
            domain=settings.SESSION_COOKIE_DOMAIN,
            samesite=settings.SESSION_COOKIE_SAMESITE,
        )
        return response
