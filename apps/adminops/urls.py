from django.urls import path

from .views import ManagedUserCollectionView, ManagedUserDetailView


app_name = "administration"
urlpatterns = [
    path("users", ManagedUserCollectionView.as_view(), name="managed-users"),
    path("users/<str:user_id>", ManagedUserDetailView.as_view(), name="managed-user-detail"),
]
