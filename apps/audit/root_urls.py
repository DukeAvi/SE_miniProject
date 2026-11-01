"""Frozen Admin audit-log route owned by the audit app."""

from django.urls import path

from .views import AuditEventListView


urlpatterns = [
    path("admin/audit-logs", AuditEventListView.as_view(), name="admin-audit-logs"),
]
