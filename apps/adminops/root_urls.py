"""Frozen `/admin` contract routes owned by the administration app."""

from django.urls import path

from .views import ManagedUserCollectionView, ManagedUserDetailView


urlpatterns = [
    path("admin/users", ManagedUserCollectionView.as_view(), name="admin-user-collection"),
    path("admin/users/<str:user_id>", ManagedUserDetailView.as_view(), name="admin-user-detail"),
]
