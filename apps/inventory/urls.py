from django.urls import path

from .views import BloodUnitCreateView, BloodUnitDiscardView, BloodUnitReturnView


app_name = "inventory"
urlpatterns = [
    path("units", BloodUnitCreateView.as_view(), name="units-create"),
    path("units/<uuid:unit_id>/discard", BloodUnitDiscardView.as_view(), name="units-discard"),
    path("units/<uuid:unit_id>/return", BloodUnitReturnView.as_view(), name="units-return"),
]
