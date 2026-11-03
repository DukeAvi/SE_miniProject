"""Exact no-trailing-slash request routes from the frozen API contract."""

from django.urls import path

from .views import (
    BloodRequestCollectionView,
    BloodRequestDecisionView,
    BloodRequestDetailView,
    BloodRequestIssueView,
    BloodRequestReservationView,
)


urlpatterns = [
    path("requests", BloodRequestCollectionView.as_view(), name="request-collection-contract"),
    path("requests/<str:request_id>", BloodRequestDetailView.as_view(), name="request-detail-contract"),
    path(
        "requests/<str:request_id>/decision",
        BloodRequestDecisionView.as_view(),
        name="request-decision-contract",
    ),
    path(
        "requests/<str:request_id>/reserve",
        BloodRequestReservationView.as_view(),
        name="request-reservation-contract",
    ),
    path(
        "requests/<str:request_id>/issue",
        BloodRequestIssueView.as_view(),
        name="request-issue-contract",
    ),
]
