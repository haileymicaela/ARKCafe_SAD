from django.urls import path

from . import project_views, user_views, views

urlpatterns = [
    path("admin-departments/", views.admin_departments, name="admin_departments"),
    path("admin-users/", user_views.admin_users, name="admin_users"),
    
    path("admin-projects/", project_views.project_list, name="project_list"),
    path("admin-projects/add/", project_views.project_add, name="project_add"),
    path("admin-projects/<int:pk>/edit/", project_views.project_edit, name="project_edit"),
    path("admin-projects/<int:pk>/delete/", project_views.project_delete, name="project_delete"),
]
