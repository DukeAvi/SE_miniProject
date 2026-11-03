from django.urls import path

from .views import (
    BloodRequestCollectionView,
    BloodRequestDecisionView,
    BloodRequestDetailView,
    BloodRequestIssueView,
    BloodRequestReservationView,
)


app_name = "requests"
urlpatterns = [
    path("", BloodRequestCollectionView.as_view(), name="request-collection"),
    path("<str:request_id>", BloodRequestDetailView.as_view(), name="request-detail"),
    path(
        "<str:request_id>/decision",
        BloodRequestDecisionView.as_view(),
        name="request-decision",
    ),
    path(
        "<str:request_id>/reserve",
        BloodRequestReservationView.as_view(),
        name="request-reservation",
    ),
    path(
        "<str:request_id>/issue",
        BloodRequestIssueView.as_view(),
        name="request-issue",
    ),
]
