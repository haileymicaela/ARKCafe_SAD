from django.urls import path
from . import project_views, user_views, views, alert_views

urlpatterns = [
    # Departments
    path(
        "admin-departments/",
        views.admin_departments,
        name="admin_departments"
    ),

    # User Accounts
    path(
        "admin-users/",
        user_views.admin_users,
        name="admin_users"
    ),

    # Projects
    path(
        "admin-projects/",
        project_views.project_list,
        name="project_list"
    ),
    path(
        "admin-projects/add/",
        project_views.project_add,
        name="project_add"
    ),
    path(
        "admin-projects/<int:pk>/edit/",
        project_views.project_edit,
        name="project_edit"
    ),
    path(
        "admin-projects/<int:pk>/delete/",
        project_views.project_delete,
        name="project_delete"
    ),

    # Alert Recipients
    path(
        "admin-recipients/",
        alert_views.recipient_list,
        name="alert_recipients"
    ),
    path(
        "admin-recipients/add/",
        alert_views.recipient_add,
        name="alert_recipient_add"
    ),
    path(
        "admin-recipients/<int:pk>/edit/",
        alert_views.recipient_edit,
        name="alert_recipient_edit"
    ),
    path(
        "admin-recipients/<int:pk>/delete/",
        alert_views.recipient_delete,
        name="alert_recipient_delete"
    ),
]