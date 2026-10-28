from django.urls import path

from .views import RegistrationView


app_name = "accounts"
urlpatterns = [
    path("auth/register", RegistrationView.as_view(), name="register"),
]
