from django.urls import path

from .views import BloodAvailabilityView, BloodUnitCollectionView


app_name = "inventory"
urlpatterns = [
    path("units", BloodUnitCollectionView.as_view(), name="units"),
    path("availability", BloodAvailabilityView.as_view(), name="availability"),
]
