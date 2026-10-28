from django.urls import include, path

from apps.core.views import healthz


urlpatterns = [
    path("healthz", healthz, name="healthz"),
    path("api/v1/", include("bbms.api_urls")),
]
