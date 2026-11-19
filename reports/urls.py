from django.urls import path
from . import views

urlpatterns = [
    # Admin Routes
    path('reports/admin/dashboard/', views.dashboard_view, name='admin_dashboard'),
    path('reports/admin/audit-history/', views.audit_history_view, name='admin_audit_history'),
    path('reports/admin/recent-activity/', views.recent_activity_view, name='admin_recent_activity'),

    # QA/QC Routes
    path('staff/dashboard/', views.dashboard_view, name='staff_dashboard'),
    path('staff/audit-history/', views.audit_history_view, name='staff_audit_history'),
    path('staff/export/', views.export_ncr_view, name='staff_export'),
]
