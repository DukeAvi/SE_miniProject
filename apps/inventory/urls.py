from django.urls import path

from .views import (
    BloodAvailabilityView,
    BloodUnitCollectionView,
    BloodUnitDiscardView,
    BloodUnitReturnView,
)

app_name = "inventory"
urlpatterns = [
    path("units", BloodUnitCollectionView.as_view(), name="units"),
    path("availability", BloodAvailabilityView.as_view(), name="availability"),
    path("units/<uuid:unit_id>/discard", BloodUnitDiscardView.as_view(), name="units-discard"),
    path("units/<uuid:unit_id>/return", BloodUnitReturnView.as_view(), name="units-return"),
]
