from django.urls import path

from .views import DonationRecordView, DonationSlotListView

urlpatterns = [
    path("donations", DonationRecordView.as_view(), name="donations"),
    path("donation-slots", DonationSlotListView.as_view(), name="donation-slots"),
]
