from django.shortcuts import render
from django.http import HttpResponse
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta
import csv

# IMPORTING FROM CORE (As instructed by team lead)
from core.models import NcrRecord, Project, ActivityLog, AuditLog, Department
from accounts.models import User

def get_filtered_ncrs(request):
    time_filter = request.GET.get('time_filter', 'all')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    ncrs = NcrRecord.objects.all()

    if time_filter == 'today':
        ncrs = ncrs.filter(issued_date=timezone.now().date())
    elif time_filter == '7_days':
        ncrs = ncrs.filter(issued_date__gte=timezone.now() - timedelta(days=7))
    elif time_filter == '30_days':
        ncrs = ncrs.filter(issued_date__gte=timezone.now() - timedelta(days=30))
    elif time_filter == 'this_year':
        ncrs = ncrs.filter(issued_date__year=timezone.now().year)
    elif time_filter == 'custom' and start_date and end_date:
        ncrs = ncrs.filter(issued_date__range=[start_date, end_date])
    
    return ncrs, time_filter

def dashboard_view(request):
    is_staff = 'staff' in request.path
    ncrs, time_filter = get_filtered_ncrs(request)
    
    # Using the shared definitions from core.models
    total_open = ncrs.filter(status__in=NcrRecord.OPEN_STATUSES).count()
    total_closed = ncrs.filter(status__in=NcrRecord.CLOSED_STATUSES).count()
    
    active_users = User.objects.filter(is_active=True).count()
    active_projects = Project.objects.count()

    # Chart Data: Cause
    causes = ['material', 'workmanship', 'sequencing']
    cause_data = []
    for cause in causes:
        open_c = ncrs.filter(cause=cause, status__in=NcrRecord.OPEN_STATUSES).count()
        closed_c = ncrs.filter(cause=cause, status__in=NcrRecord.CLOSED_STATUSES).count()
        cause_data.append({'cause': cause.title(), 'open': open_c, 'closed': closed_c})

    # Chart Data: Project
    project_data = []
    for proj in Project.objects.all()[:5]:
        open_p = ncrs.filter(project=proj, status__in=NcrRecord.OPEN_STATUSES).count()
        closed_p = ncrs.filter(project=proj, status__in=NcrRecord.CLOSED_STATUSES).count()
        project_data.append({'project': proj.project_name, 'open': open_p, 'closed': closed_p})

    # Recent Activity (Only for Admin)
    recent_activities = ActivityLog.objects.select_related('user').order_by('-created_at')[:5] if not is_staff else []

    context = {
        'total_open': total_open,
        'total_closed': total_closed,
        'active_users': active_users,
        'active_projects': active_projects,
        'cause_data': cause_data,
        'project_data': project_data,
        'recent_activities': recent_activities,
        'time_filter': time_filter,
        'is_staff': is_staff,
    }
    return render(request, 'reports/dashboard.html', context)

def audit_history_view(request):
    logs = AuditLog.objects.select_related('ncr', 'user').order_by('-changed_at')
    
    search_query = request.GET.get('q', '')
    if search_query:
        logs = logs.filter(
            Q(ncr__reference_no__icontains=search_query) | 
            Q(user__full_name__icontains=search_query) |
            Q(remarks__icontains=search_query)
        )
    
    paginator = Paginator(logs, 10)
    page_obj = paginator.get_page(request.GET.get('page'))
    
    return render(request, 'reports/audit_history.html', {
        'page_obj': page_obj, 
        'search_query': search_query, 
        'is_staff': 'staff' in request.path
    })

def recent_activity_view(request):
    activities = ActivityLog.objects.select_related('user').order_by('-created_at')
    paginator = Paginator(activities, 10)
    return render(request, 'reports/recent_activity.html', {'page_obj': paginator.get_page(request.GET.get('page'))})

def export_ncr_view(request):
    if request.method == 'POST':
        export_type = request.POST.get('export_type', 'excel')
        if export_type == 'excel':
            ncrs, _ = get_filtered_ncrs(request)
            
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename="NCR_Export.csv"'
            writer = csv.writer(response)
            writer.writerow(['NCR No', 'Subject', 'Project', 'Cause', 'Status', 'Date Raised'])
            
            for ncr in ncrs:
                writer.writerow([
                    ncr.reference_no, 
                    ncr.subject, 
                    ncr.project.project_name, 
                    ncr.get_cause_display(), # Using Django's get_display for choices
                    ncr.get_status_display(), 
                    ncr.issued_date
                ])
            return response
        elif export_type == 'pdf':
            pass 

    projects = Project.objects.all()
    ncrs = NcrRecord.objects.all()[:20]
    filtered_ncrs, _ = get_filtered_ncrs(request)
    
    return render(request, 'reports/export_ncr.html', {
        'projects': projects, 
        'ncrs': ncrs, 
        'total_records': filtered_ncrs.count()
    })