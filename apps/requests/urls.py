from django.urls import path

from .views import (
    BloodRequestCollectionView,
    BloodRequestDecisionView,
    BloodRequestDetailView,
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
]
