"""Exact no-trailing-slash notification routes from the API contract."""

from django.urls import path

from .views import NotificationCollectionView, NotificationFailureCollectionView


urlpatterns = [
    path("notifications", NotificationCollectionView.as_view(), name="notification-list-contract"),
    path("admin/notification-failures", NotificationFailureCollectionView.as_view(), name="notification-failures-contract"),
]
