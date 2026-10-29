from django.urls import path

from .views import MyDonationHistoryView

app_name = "donors"
urlpatterns = [path("me/donations", MyDonationHistoryView.as_view(), name="my-donations")]
