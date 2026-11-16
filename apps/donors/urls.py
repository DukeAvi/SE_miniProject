from django.urls import path

from .onboarding_views import StaffDonorLookupView, StaffDonorProfileCreateView
from .views import AppointmentCancelView, MyAppointmentListCreateView, MyDonationHistoryView

app_name = "donors"
urlpatterns = [
    path("staff/donors", StaffDonorLookupView.as_view(), name="staff-donor-lookup"),
    path("staff/donor-profiles", StaffDonorProfileCreateView.as_view(), name="staff-donor-profile-create"),
    path("me/donations", MyDonationHistoryView.as_view(), name="my-donations"),
    path("me/appointments", MyAppointmentListCreateView.as_view(), name="my-appointments"),
    path("me/appointments/<str:appointment_id>/cancel", AppointmentCancelView.as_view(), name="cancel-appointment"),
]
