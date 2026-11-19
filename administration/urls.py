from django.urls import path

from . import user_views, views

urlpatterns = [
    path("admin-departments/", views.admin_departments, name="admin_departments"),
    path("admin-users/", user_views.admin_users, name="admin_users"),
]
