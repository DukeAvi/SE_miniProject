"""Exact no-trailing-slash request routes from the frozen API contract."""

from django.urls import path

from .views import BloodRequestCollectionView


urlpatterns = [
    path("requests", BloodRequestCollectionView.as_view(), name="request-collection-contract"),
]
