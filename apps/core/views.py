from uuid import uuid4

from django.http import JsonResponse


def healthz(request):
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
