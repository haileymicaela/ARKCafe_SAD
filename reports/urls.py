from django.urls import path
from . import views
from core.decorators import admin_required, staff_required

urlpatterns = [
    # Admin Routes
    path('reports/admin/dashboard/', admin_required(views.dashboard_view), name='admin_dashboard'),
    path('reports/admin/audit-history/', admin_required(views.audit_history_view), name='admin_audit_history'),
    path('reports/admin/recent-activity/', admin_required(views.recent_activity_view), name='admin_recent_activity'),

    # QA/QC Routes
    path('staff/dashboard/', staff_required(views.dashboard_view), name='staff_dashboard'),
    path('staff/audit-history/', staff_required(views.audit_history_view), name='staff_audit_history'),
    path('staff/export/', staff_required(views.export_ncr_view), name='staff_export'),
]
