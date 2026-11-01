from django.urls import path

from .views import BloodRequestCollectionView


app_name = "requests"
urlpatterns = [
    path("", BloodRequestCollectionView.as_view(), name="request-collection"),
]
