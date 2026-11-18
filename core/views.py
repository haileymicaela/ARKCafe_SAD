from django.shortcuts import render

from .decorators import admin_required, staff_required

# --- Admin Views ---
@admin_required
def admin_dashboard(request):
    return render(request, 'base.html')

@admin_required
def admin_projects(request):
    return render(request, 'base.html')

@admin_required
def admin_departments(request):
    return render(request, 'base.html')

@admin_required
def admin_users(request):
    return render(request, 'base.html')

@admin_required
def admin_recipients(request):
    return render(request, 'base.html')

@admin_required
def admin_audit(request):
    return render(request, 'base.html')

# --- Staff (QA/QC) Views ---
@staff_required
def staff_dashboard(request):
    return render(request, 'base.html')

@staff_required
def staff_records(request):
    return render(request, 'base.html')

@staff_required
def staff_create_ncr(request):
    return render(request, 'base.html')

@staff_required
def staff_recipients(request):
    return render(request, 'base.html')

@staff_required
def staff_export(request):
    return render(request, 'base.html')

@staff_required
def staff_audit(request):
    return render(request, 'base.html')