from django.urls import path
from django.views.generic import RedirectView
from . import views

urlpatterns = [
    # ROOT URL: sends the user to the right dashboard (or to login if not logged in)
    path('', RedirectView.as_view(pattern_name='home', permanent=False)),
    path('home/', views.home, name='home'),

    # Admin URLs
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('admin-projects/', views.admin_projects, name='admin_projects'),
    path('admin-departments/', views.admin_departments, name='admin_departments'),
    path('admin-users/', views.admin_users, name='admin_users'),
    path('admin-recipients/', views.admin_recipients, name='admin_recipients'),
    path('admin-audit/', views.admin_audit, name='admin_audit'),

    # Staff URLs
    path('staff-dashboard/', views.staff_dashboard, name='staff_dashboard'),
    path('staff-records/', views.staff_records, name='staff_records'),
    path('staff-create/', views.staff_create_ncr, name='staff_create_ncr'),
    path('staff-recipients/', views.staff_recipients, name='staff_recipients'),
    path('staff-export/', views.staff_export, name='staff_export'),
    path('staff-audit/', views.staff_audit, name='staff_audit'),
]