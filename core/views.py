from django.shortcuts import render

# --- Admin Views ---
def admin_dashboard(request):
    return render(request, 'base.html')

def admin_projects(request):
    return render(request, 'base.html')

def admin_departments(request):
    return render(request, 'base.html')

def admin_users(request):
    return render(request, 'base.html')

def admin_recipients(request):
    return render(request, 'base.html')

def admin_audit(request):
    return render(request, 'base.html')

# --- Staff (QA/QC) Views ---
def staff_dashboard(request):
    return render(request, 'base.html')

def staff_records(request):
    return render(request, 'base.html')

def staff_create_ncr(request):
    return render(request, 'base.html')

def staff_recipients(request):
    return render(request, 'base.html')

def staff_export(request):
    return render(request, 'base.html')

def staff_audit(request):
    return render(request, 'base.html')