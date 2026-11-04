"""Low-cardinality HTTP latency metrics for Prometheus."""

import time

from prometheus_client import Histogram


REQUEST_LATENCY = Histogram(
    "bbms_http_request_duration_seconds",
    "HTTP request latency by resolved Django route, method, and status code.",
    labelnames=("route", "method", "status_code"),
    buckets=(0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 3.0, 5.0, 10.0, 30.0),
)


class RequestLatencyMiddleware:
    """Record request latency without labels containing user data or identifiers."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path == "/metrics":
            return self.get_response(request)

        started_at = time.perf_counter()
        response = self.get_response(request)
        route = getattr(getattr(request, "resolver_match", None), "route", None) or "unmatched"
        REQUEST_LATENCY.labels(
            route=route,
            method=request.method,
            status_code=str(response.status_code),
        ).observe(time.perf_counter() - started_at)
        return response
