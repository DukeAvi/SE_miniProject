from django.urls import include, path

from apps.core.views import healthz
from apps.core.metrics_views import metrics


urlpatterns = [
    path("healthz", healthz, name="healthz"),
    path("metrics", metrics, name="metrics"),
    path("api/v1/", include("bbms.api_urls")),
]
