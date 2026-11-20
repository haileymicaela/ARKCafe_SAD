from django.urls import path
from django.views.generic import RedirectView # <-- Add this import
from . import views

urlpatterns = [
    # ROOT URL: redirects to login (logged-in users are then sent on to their dashboard)
    path('', RedirectView.as_view(pattern_name='login', permanent=False)),

    # Admin URLs
    path('admin-dashboard/', views.admin_dashboard, name='core_admin_dashboard'),
    path('admin-projects/', views.admin_projects, name='admin_projects'),
    path('admin-departments/', views.admin_departments, name='admin_departments'),
    path('admin-users/', views.admin_users, name='admin_users'),
    path('admin-recipients/', views.admin_recipients, name='admin_recipients'),
    path('admin-audit/', views.admin_audit, name='admin_audit'),

    # Staff URLs
    path('staff-dashboard/', views.staff_dashboard, name='core_staff_dashboard'),
    path('staff-records/', views.staff_records, name='staff_records'),
    path('staff-create/', views.staff_create_ncr, name='staff_create_ncr'),
    path('staff-recipients/', views.staff_recipients, name='staff_recipients'),
    path('staff-export/', views.staff_export, name='core_staff_export'),
    path('staff-audit/', views.staff_audit, name='staff_audit'),
]
