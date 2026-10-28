from django.urls import path

from .views import CsrfTokenView, CurrentProfileView, LoginView, LogoutView, RegistrationView


app_name = "accounts"
urlpatterns = [
    path("auth/register", RegistrationView.as_view(), name="register"),
    path("auth/csrf", CsrfTokenView.as_view(), name="csrf"),
    path("auth/login", LoginView.as_view(), name="login"),
    path("auth/logout", LogoutView.as_view(), name="logout"),
    path("users/me", CurrentProfileView.as_view(), name="current-profile"),
]
