from django.contrib.auth.views import LogoutView
from django.urls import path

from .views import CrimsonLoginView

urlpatterns = [
    path("login/", CrimsonLoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
]
