from django.contrib.auth.decorators import login_required
from django.shortcuts import render

# --- Admin Views ---
@login_required
def admin_dashboard(request):
    return render(request, 'base.html')

@login_required
def admin_projects(request):
    return render(request, 'base.html')

@login_required
def admin_departments(request):
    return render(request, 'base.html')

@login_required
def admin_users(request):
    return render(request, 'base.html')

@login_required
def admin_recipients(request):
    return render(request, 'base.html')

@login_required
def admin_audit(request):
    return render(request, 'base.html')

# --- Staff (QA/QC) Views ---
@login_required
def staff_dashboard(request):
    return render(request, 'base.html')

@login_required
def staff_records(request):
    return render(request, 'base.html')

@login_required
def staff_create_ncr(request):
    return render(request, 'base.html')

@login_required
def staff_recipients(request):
    return render(request, 'base.html')

@login_required
def staff_export(request):
    return render(request, 'base.html')

@login_required
def staff_audit(request):
    return render(request, 'base.html')