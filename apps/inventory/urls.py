from django.urls import path

from .views import BloodUnitCreateView


app_name = "inventory"
urlpatterns = [
    path("units", BloodUnitCreateView.as_view(), name="units-create"),
]
