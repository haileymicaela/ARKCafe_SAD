from django.urls import path

from . import views

urlpatterns = [
    path("admin-departments/", views.admin_departments, name="admin_departments"),
]