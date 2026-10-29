from django.urls import path

from .views import AppointmentCancelView, MyAppointmentListCreateView, MyDonationHistoryView

app_name = "donors"
urlpatterns = [
    path("me/donations", MyDonationHistoryView.as_view(), name="my-donations"),
    path("me/appointments", MyAppointmentListCreateView.as_view(), name="my-appointments"),
    path("me/appointments/<str:appointment_id>/cancel", AppointmentCancelView.as_view(), name="cancel-appointment"),
]
