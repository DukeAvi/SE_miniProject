from django.urls import path

from .views import AuditEventListView


app_name = "audit"
urlpatterns = [
    path("logs", AuditEventListView.as_view(), name="audit-logs"),
]
