"""Frozen `/admin` contract routes owned by the administration app."""

from django.urls import path

from .views import (
    ManagedUserCollectionView,
    ManagedUserDetailView,
    StockThresholdCollectionView,
)


urlpatterns = [
    path("admin/users", ManagedUserCollectionView.as_view(), name="admin-user-collection"),
    path("admin/users/<str:user_id>", ManagedUserDetailView.as_view(), name="admin-user-detail"),
    path("admin/stock-thresholds", StockThresholdCollectionView.as_view(), name="stock-thresholds"),
]
