from django.urls import path

from .views import BloodRequestCollectionView, BloodRequestDecisionView


app_name = "requests"
urlpatterns = [
    path("", BloodRequestCollectionView.as_view(), name="request-collection"),
    path(
        "<str:request_id>/decision",
        BloodRequestDecisionView.as_view(),
        name="request-decision",
    ),
]
