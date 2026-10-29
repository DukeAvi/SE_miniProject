from django.urls import include, path


app_name = "api-v1"

urlpatterns = [
    path("", include("apps.accounts.urls")),
    path("", include("apps.donors.donation_urls")),
    path("donors/", include("apps.donors.urls")),
    path("inventory/", include("apps.inventory.urls")),
    path("requests/", include("apps.requests.urls")),
    path("notifications/", include("apps.notifications.urls")),
    path("administration/", include("apps.adminops.urls")),
    path("audit/", include("apps.audit.urls")),
]
