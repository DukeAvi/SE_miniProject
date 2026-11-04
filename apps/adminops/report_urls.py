"""Routes for the report API contract."""

from django.urls import path

from .report_views import OperationalReportView


urlpatterns = [
    path("reports/<str:resource>", OperationalReportView.as_view(), name="operational-report"),
]
