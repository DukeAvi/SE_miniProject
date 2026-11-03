"""Exact no-trailing-slash request routes from the frozen API contract."""

from django.urls import path

from .views import (
    BloodRequestCollectionView,
    BloodRequestDecisionView,
    BloodRequestDetailView,
)


urlpatterns = [
    path("requests", BloodRequestCollectionView.as_view(), name="request-collection-contract"),
    path("requests/<str:request_id>", BloodRequestDetailView.as_view(), name="request-detail-contract"),
    path(
        "requests/<str:request_id>/decision",
        BloodRequestDecisionView.as_view(),
        name="request-decision-contract",
    ),
]
