"""Internal Prometheus exposition endpoint."""

import os
import hmac

from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_GET
from prometheus_client import CONTENT_TYPE_LATEST, CollectorRegistry, generate_latest, multiprocess
from prometheus_client import REGISTRY


@require_GET
def metrics(request):
    token = settings.PROMETHEUS_METRICS_BEARER_TOKEN
    if not token:
        return JsonResponse({"status": "unavailable"}, status=503)
    supplied = request.META.get("HTTP_AUTHORIZATION", "")
    if not hmac.compare_digest(supplied, f"Bearer {token}"):
        return JsonResponse({"status": "forbidden"}, status=403)
    if os.environ.get("PROMETHEUS_MULTIPROC_DIR"):
        registry = CollectorRegistry()
        multiprocess.MultiProcessCollector(registry)
    else:
        registry = REGISTRY
    return HttpResponse(generate_latest(registry), content_type=CONTENT_TYPE_LATEST)
