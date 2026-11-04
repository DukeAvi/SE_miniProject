from uuid import uuid4

from django.db import DatabaseError, connection
from django.http import JsonResponse
from django.views.decorators.http import require_GET


@require_GET
def healthz(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except DatabaseError:
        return JsonResponse({"status": "unavailable"}, status=503)
    return JsonResponse({"status": "ok"})


def csrf_failure(request, reason=""):
    return JsonResponse(
        {
            "error": {
                "code": "csrf_failed",
                "message": "CSRF verification failed.",
                "details": {},
                "correlation_id": str(uuid4()),
            }
        },
        status=403,
    )
