from django.shortcuts import render
from django.http import HttpResponse
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.utils import timezone
from datetime import date, timedelta
import csv

# IMPORTING FROM CORE (As instructed by team lead)
from core.models import NcrRecord, Project, ActivityLog, AuditLog, Department
from accounts.models import User

def get_filtered_ncrs(request):
    time_filter = request.GET.get('time_filter', 'all')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    today = timezone.localdate()
    supported_filters = {'all', 'today', '7_days', '30_days', '3_months', 'this_month', 'this_quarter', 'this_year', 'custom'}
    if time_filter not in supported_filters:
        time_filter = 'all'
    
    ncrs = NcrRecord.objects.all()

    if time_filter == 'today':
        ncrs = ncrs.filter(issued_date=today)
    elif time_filter == '7_days':
        ncrs = ncrs.filter(issued_date__gte=today - timedelta(days=6))
    elif time_filter == '30_days':
        ncrs = ncrs.filter(issued_date__gte=today - timedelta(days=29))
    elif time_filter == '3_months':
        ncrs = ncrs.filter(issued_date__gte=today - timedelta(days=89))
    elif time_filter == 'this_month':
        ncrs = ncrs.filter(issued_date__year=today.year, issued_date__month=today.month)
    elif time_filter == 'this_quarter':
        quarter_start_month = ((today.month - 1) // 3) * 3 + 1
        ncrs = ncrs.filter(
            issued_date__year=today.year,
            issued_date__month__gte=quarter_start_month,
            issued_date__month__lte=quarter_start_month + 2,
        )
    elif time_filter == 'this_year':
        ncrs = ncrs.filter(issued_date__year=today.year)
    elif time_filter == 'custom':
        try:
            start = date.fromisoformat(start_date or '')
            end = date.fromisoformat(end_date or '')
        except ValueError:
            time_filter = 'all'
        else:
            if start <= end:
                ncrs = ncrs.filter(issued_date__range=[start, end])
            else:
                time_filter = 'all'
    
    return ncrs, time_filter

def get_dashboard_date_range(time_filter, start_date=None, end_date=None):
    today = timezone.localdate()
    if time_filter == 'today':
        return today, today
    if time_filter == '7_days':
        return today - timedelta(days=6), today
    if time_filter == '30_days':
        return today - timedelta(days=29), today
    if time_filter == '3_months':
        return today - timedelta(days=89), today
    if time_filter == 'this_month':
        return today.replace(day=1), today
    if time_filter == 'this_quarter':
        quarter_start_month = ((today.month - 1) // 3) * 3 + 1
        return today.replace(month=quarter_start_month, day=1), today
    if time_filter == 'this_year':
        return today.replace(month=1, day=1), today
    if time_filter == 'custom':
        try:
            start = date.fromisoformat(start_date or '')
            end = date.fromisoformat(end_date or '')
        except ValueError:
            return None, None
        if start <= end:
            return start, end
    return None, None

def dashboard_view(request):
    is_staff = 'staff' in request.path
    ncrs, time_filter = get_filtered_ncrs(request)
    selected_start, selected_end = get_dashboard_date_range(
        time_filter, request.GET.get('start_date'), request.GET.get('end_date')
    )
    
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
        'selected_start': selected_start,
        'selected_end': selected_end,
        'dashboard_date_presets': (
            ('today', 'Today'),
            ('7_days', 'Last 7 days'),
            ('30_days', 'Last 30 days'),
            ('3_months', 'Last 3 months'),
            ('this_month', 'This month'),
            ('this_quarter', 'This quarter'),
            ('this_year', 'This year'),
            ('all', 'All time'),
        ),
        'is_staff': is_staff,
    }
    return render(request, 'reports/dashboard.html', context)

def audit_history_view(request):
    logs = AuditLog.objects.select_related('ncr', 'user')
    
    search_query = request.GET.get('q', '').strip()
    if search_query:
        logs = logs.filter(
            Q(ncr__reference_no__icontains=search_query) | 
            Q(user__full_name__icontains=search_query) |
            Q(remarks__icontains=search_query)
        )

    status_filter = request.GET.get('status', '')
    if status_filter in dict(NcrRecord.STATUS_CHOICES):
        logs = logs.filter(new_status=status_filter)
    else:
        status_filter = ''

    start_date = end_date = None
    try:
        start_date = date.fromisoformat(request.GET.get('start_date', '')) if request.GET.get('start_date') else None
        end_date = date.fromisoformat(request.GET.get('end_date', '')) if request.GET.get('end_date') else None
    except ValueError:
        start_date = end_date = None
    if start_date and end_date and start_date > end_date:
        start_date, end_date = end_date, start_date
    if start_date:
        logs = logs.filter(changed_at__date__gte=start_date)
    if end_date:
        logs = logs.filter(changed_at__date__lte=end_date)

    ordering = 'oldest' if request.GET.get('ordering') == 'oldest' else 'newest'
    logs = logs.order_by('changed_at', 'history_id') if ordering == 'oldest' else logs.order_by('-changed_at', '-history_id')
    
    paginator = Paginator(logs, 10)
    page_obj = paginator.get_page(request.GET.get('page'))
    query_params = request.GET.copy()
    query_params.pop('page', None)
    
    return render(request, 'reports/audit_history.html', {
        'page_obj': page_obj, 
        'search_query': search_query, 
        'status_choices': NcrRecord.STATUS_CHOICES,
        'status_filter': status_filter,
        'start_date': start_date,
        'end_date': end_date,
        'ordering': ordering,
        'query_string': query_params.urlencode(),
        'is_staff': 'staff' in request.path
    })

def recent_activity_view(request):
    activities = ActivityLog.objects.select_related('user').order_by('-created_at')
    search_query = request.GET.get('q', '').strip()
    if search_query:
        activities = activities.filter(
            Q(user__full_name__icontains=search_query)
            | Q(entity_label__icontains=search_query)
            | Q(entity_type__icontains=search_query)
        )

    entity_filter = request.GET.get('entity', '')
    action_filter = request.GET.get('action', '')
    entity_options = sorted(
        value for value in ActivityLog.objects.order_by().values_list('entity_type', flat=True).distinct() if value
    )
    action_options = sorted(
        value for value in ActivityLog.objects.order_by().values_list('action_type', flat=True).distinct() if value
    )

    if entity_filter in entity_options:
        activities = activities.filter(entity_type=entity_filter)
    else:
        entity_filter = ''
    if action_filter in action_options:
        activities = activities.filter(action_type=action_filter)
    else:
        action_filter = ''

    time_filter = request.GET.get('time_filter', 'all')
    today = timezone.localdate()
    start_date = end_date = None
    if time_filter == 'today':
        start_date = end_date = today
    elif time_filter == '7_days':
        start_date, end_date = today - timedelta(days=6), today
    elif time_filter == '30_days':
        start_date, end_date = today - timedelta(days=29), today
    elif time_filter == 'custom':
        try:
            start_date = date.fromisoformat(request.GET.get('start_date', ''))
            end_date = date.fromisoformat(request.GET.get('end_date', ''))
        except ValueError:
            time_filter = 'all'
            start_date = end_date = None
        if time_filter == 'custom' and start_date > end_date:
            time_filter = 'all'
            start_date = end_date = None
    elif time_filter not in {'all', 'today', '7_days', '30_days'}:
        time_filter = 'all'

    if start_date and end_date:
        activities = activities.filter(created_at__date__range=(start_date, end_date))

    paginator = Paginator(activities, 10)
    query_params = request.GET.copy()
    query_params.pop('page', None)
    return render(request, 'reports/recent_activity.html', {
        'page_obj': paginator.get_page(request.GET.get('page')),
        'search_query': search_query,
        'entity_options': entity_options,
        'action_options': action_options,
        'entity_filter': entity_filter,
        'action_filter': action_filter,
        'time_filter': time_filter,
        'start_date': start_date,
        'end_date': end_date,
        'query_string': query_params.urlencode(),
    })

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
