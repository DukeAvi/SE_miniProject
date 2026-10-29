from django.urls import path

from .views import DonationRecordView

urlpatterns = [path("donations", DonationRecordView.as_view(), name="donations")]
