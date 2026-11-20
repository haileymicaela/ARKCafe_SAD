from django.shortcuts import render
from django.http import HttpResponse
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.utils import timezone
from datetime import date, timedelta
import re
import zipfile
from io import BytesIO
from xml.sax.saxutils import escape

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
    entity_filters = {
        'user': ('user', 'user_account'),
        'project': ('project',),
        'department': ('department',),
        'recipient': ('recipient', 'alert_recipient'),
    }
    entity_labels = {
        'user': 'User',
        'project': 'Project',
        'department': 'Department',
        'recipient': 'Recipient',
    }
    action_filters = {
        'create': ('create', 'created'),
        'update': ('update', 'updated'),
        'rename': ('rename', 'renamed'),
        'delete': ('delete', 'deleted'),
        'password_reset': ('password_reset', 'password-reset', 'password reset'),
        'activate': ('activate', 'activated'),
        'deactivate': ('deactivate', 'deactivated'),
    }
    action_labels = {
        'create': 'Created',
        'update': 'Updated',
        'rename': 'Renamed',
        'delete': 'Deleted',
        'password_reset': 'Password reset',
        'activate': 'Activated',
        'deactivate': 'Deactivated',
    }
    entity_options = [(key, entity_labels[key]) for key in entity_filters]
    action_options = [(key, action_labels[key]) for key in action_filters]

    if entity_filter in entity_filters:
        activities = activities.filter(entity_type__in=entity_filters[entity_filter])
    elif entity_filter in {value for value, _ in entity_options}:
        activities = activities.filter(entity_type=entity_filter)
    else:
        entity_filter = ''
    if action_filter in action_filters:
        activities = activities.filter(action_type__in=action_filters[action_filter])
    elif action_filter in {value for value, _ in action_options}:
        activities = activities.filter(action_type=action_filter)
    else:
        action_filter = ''

    entity_filter_label = dict(entity_options).get(entity_filter, '')
    action_filter_label = dict(action_options).get(action_filter, '')

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
        'entity_filter_label': entity_filter_label,
        'action_filter_label': action_filter_label,
        'time_filter': time_filter,
        'start_date': start_date,
        'end_date': end_date,
        'query_string': query_params.urlencode(),
    })

def export_ncr_view(request):
    if request.method == 'POST':
        export_type = request.POST.get('export_type', 'excel')
        if export_type not in {'excel', 'pdf'}:
            return JsonResponse({'error': 'Choose a valid export format.'}, status=400)

        if export_type == 'pdf':
            ncr = NcrRecord.objects.select_related(
                'project', 'department', 'created_by'
            ).filter(pk=request.POST.get('single_ncr')).first()
            if not ncr:
                return JsonResponse({'error': 'Select an NCR to export.'}, status=400)
            options = {
                'attachments': request.POST.get('include_attachments') == 'on',
                'history': request.POST.get('include_history') == 'on',
                'resolution': request.POST.get('include_resolution') == 'on',
            }
            content = _build_ncr_pdf(ncr, options)
            filename = f'{_safe_filename(ncr.reference_no)}.pdf'
            response = HttpResponse(content, content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            response['X-Export-Records'] = '1'
            response['X-Export-Filename'] = filename
            return response

        queryset = _filtered_export_ncrs(request.POST)
        if request.POST.get('preview') == '1':
            return JsonResponse({
                'records': queryset.count(),
                'filename': f'NCR-List_{timezone.localdate():%Y-%m-%d}.xlsx',
            })
        columns = [value for value in request.POST.getlist('columns') if value in EXPORT_COLUMNS]
        if not columns:
            return JsonResponse({'error': 'Select at least one column to include.'}, status=400)
        records = list(queryset)
        filename = f'NCR-List_{timezone.localdate():%Y-%m-%d}.xlsx'
        response = HttpResponse(
            _build_xlsx(records, columns),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        response['X-Export-Records'] = str(len(records))
        response['X-Export-Filename'] = filename
        return response

    queryset = NcrRecord.objects.select_related('project').order_by('-issued_date', '-ncr_id')
    return render(request, 'reports/export_ncr.html', {
        'projects': Project.objects.order_by('project_name'),
        'ncrs': queryset,
        'total_records': queryset.count(),
        'today': timezone.localdate(),
        'cause_choices': NcrRecord.CAUSE_CHOICES,
        'status_choices': NcrRecord.STATUS_CHOICES,
        'column_options': EXPORT_COLUMNS,
    })


EXPORT_COLUMNS = {
    'reference_no': 'NCR No.',
    'subject': 'Subject',
    'project': 'Project',
    'package_no': 'Package No.',
    'cause': 'Cause',
    'status': 'Status',
    'issued_date': 'Date Raised',
    'resolve_date': 'Date Resolved',
    'days_open': 'Days Open',
    'department': 'Department',
    'created_by': 'Created By',
}


def _filtered_export_ncrs(data):
    queryset = NcrRecord.objects.select_related('project', 'department', 'created_by').all()
    project_id = (data.get('project') or '').strip()
    if project_id:
        if project_id.isdecimal():
            queryset = queryset.filter(project_id=int(project_id))
        else:
            return queryset.none()

    cause = (data.get('cause') or '').strip()
    if cause:
        if cause in dict(NcrRecord.CAUSE_CHOICES):
            queryset = queryset.filter(cause=cause)
        else:
            return queryset.none()

    status = (data.get('status') or '').strip()
    if status:
        if status in dict(NcrRecord.STATUS_CHOICES):
            queryset = queryset.filter(status=status)
        else:
            return queryset.none()

    package_no = (data.get('package_no') or '').strip()
    if package_no:
        queryset = queryset.filter(package_no__icontains=package_no)

    start_value = (data.get('start_date') or '').strip()
    end_value = (data.get('end_date') or '').strip()
    try:
        start = date.fromisoformat(start_value) if start_value else None
        end = date.fromisoformat(end_value) if end_value else None
    except ValueError:
        return queryset.none()
    if start and end and start > end:
        start, end = end, start
    if start:
        queryset = queryset.filter(issued_date__gte=start)
    if end:
        queryset = queryset.filter(issued_date__lte=end)
    return queryset.order_by('-issued_date', '-ncr_id')


def _safe_filename(value):
    return re.sub(r'[^A-Za-z0-9._-]+', '-', value).strip('-') or 'NCR'


def _xlsx_cell(value, row, col, styles=False):
    ref = f'{col}{row}'
    if value is None:
        return f'<c r="{ref}"/>'
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return f'<c r="{ref}" t="n"><v>{value}</v></c>'
    text = escape(str(value))
    return f'<c r="{ref}" t="inlineStr"><is><t xml:space="preserve">{text}</t></is></c>'


def _build_xlsx(records, columns):
    labels = [EXPORT_COLUMNS[key] for key in columns]
    today = timezone.localdate()
    rows = [labels]
    for ncr in records:
        values = {
            'reference_no': ncr.reference_no,
            'subject': ncr.subject,
            'project': ncr.project.project_name,
            'package_no': ncr.package_no,
            'cause': ncr.get_cause_display(),
            'status': ncr.get_status_display(),
            'issued_date': ncr.issued_date,
            'resolve_date': ncr.resolve_date,
            'days_open': ((ncr.resolve_date or today) - ncr.issued_date).days if ncr.issued_date else '',
            'department': ncr.department.department_name,
            'created_by': ncr.created_by.full_name,
        }
        rows.append([values[key] for key in columns])
    def column_name(number):
        result = ''
        while number:
            number, remainder = divmod(number - 1, 26)
            result = chr(65 + remainder) + result
        return result
    sheet_rows = []
    for row_index, row in enumerate(rows, 1):
        cells = ''.join(_xlsx_cell(value, row_index, column_name(i)) for i, value in enumerate(row, 1))
        sheet_rows.append(f'<row r="{row_index}">{cells}</row>')
    last_col = column_name(len(labels))
    sheet = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f'<dimension ref="A1:{last_col}{len(rows)}"/><sheetViews><sheetView workbookViewId="0">'
        '<pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/>'
        '</sheetView></sheetViews><sheetFormatPr defaultRowHeight="18"/><sheetData>'
        + ''.join(sheet_rows) + '</sheetData><autoFilter ref="A1:' + last_col + str(len(rows)) + '"/>'
        '</worksheet>'
    )
    workbook = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        '<sheets><sheet name="NCR List" sheetId="1" r:id="rId1"/></sheets></workbook>')
    files = {
        '[Content_Types].xml': ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
            '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
            '</Types>'),
        '_rels/.rels': ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
            '</Relationships>'),
        'xl/workbook.xml': workbook,
        'xl/_rels/workbook.xml.rels': ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
            '</Relationships>'),
        'xl/worksheets/sheet1.xml': sheet,
    }
    output = BytesIO()
    with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as archive:
        for filename, content in files.items():
            archive.writestr(filename, content)
    return output.getvalue()


def _build_ncr_pdf(ncr, options):
    attachments = list(ncr.attachments.order_by('uploaded_at')) if options['attachments'] else []
    lines = [
        'NON-CONFORMANCE REPORT', '', f'NCR: {ncr.reference_no}', f'Subject: {ncr.subject}',
        f'Project: {ncr.project.project_name}', f'Package: {ncr.package_no or "-"}',
        f'Cause: {ncr.get_cause_display()}', f'Status: {ncr.get_status_display()}',
        f'Date raised: {ncr.issued_date or "-"}', f'Required date: {ncr.required_date or "-"}',
        f'Department: {ncr.department.department_name}', f'Created by: {ncr.created_by.full_name}',
        '', 'Description:', ncr.description or '-',
    ]
    if options['resolution']:
        lines += ['', 'Resolution details:', f'Resolved: {ncr.resolve_date or "-"}',
            f'Resolution: {ncr.get_resolution_type_display() if ncr.resolution_type else "-"}',
            ncr.resolution_note or '-']
    if options['history']:
        lines += ['', 'Status history:']
        for entry in ncr.audit_entries.select_related('user').order_by('changed_at'):
            lines.append(f'{entry.changed_at:%Y-%m-%d %H:%M}  {entry.user.full_name}: {entry.old_status or "New"} -> {entry.new_status}')
            if entry.remarks:
                lines.append('  ' + entry.remarks)
    if options['attachments']:
        lines += ['', f'Attachments ({len(attachments)}):']
        lines += [f'{attachment.file_name} ({attachment.file_type})' for attachment in attachments] or ['None']
        if attachments:
            lines += ['Attachment files are embedded in this PDF.']
    escaped = []
    for line in lines:
        line = str(line).encode('ascii', 'replace').decode('ascii')
        escaped.append(line.replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')[:110])
    pages = [escaped[i:i + 48] for i in range(0, len(escaped), 48)] or [[]]
    objects = [b'<< /Type /Catalog /Pages 2 0 R >>', None,
        b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>']
    page_ids = []
    for page_lines in pages:
        page_id = len(objects) + 1
        stream_id = page_id + 1
        page_ids.append(page_id)
        commands = ['BT', '/F1 10 Tf', '50 790 Td', '14 TL']
        for line in page_lines:
            commands.append(f'({line}) Tj T*')
        commands.append('ET')
        stream = '\n'.join(commands).encode('latin-1')
        objects.append(f'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 842] /Resources << /Font << /F1 3 0 R >> >> /Contents {stream_id} 0 R >>'.encode())
        objects.append(b'<< /Length ' + str(len(stream)).encode() + b' >>\nstream\n' + stream + b'\nendstream')
    kids = ' '.join(f'{page_id} 0 R' for page_id in page_ids)
    objects[1] = f'<< /Type /Pages /Kids [{kids}] /Count {len(page_ids)} >>'.encode()
    embedded_names = []
    photo_pages = []
    for attachment in attachments:
        embedded_id = len(objects) + 1
        data = bytes(attachment.file_data)
        mime = (attachment.file_type or 'application/octet-stream').replace('/', '#2F').replace(';', '#3B')
        objects.append(
            f'<< /Type /EmbeddedFile /Subtype /{mime} /Length {len(data)} >>\nstream\n'.encode()
            + data + b'\nendstream'
        )
        filespec_id = len(objects) + 1
        safe_name = attachment.file_name.encode('ascii', 'replace').decode('ascii')
        safe_name = safe_name.replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')
        objects.append(
            f'<< /Type /Filespec /F ({safe_name}) /UF ({safe_name}) /EF << /F {embedded_id} 0 R >> >>'.encode()
        )
        embedded_names.append(f'({safe_name}) {filespec_id} 0 R')
        dimensions = _jpeg_dimensions(data) if (attachment.file_type or '').lower() in {'image/jpeg', 'image/jpg'} else None
        if dimensions:
            photo_pages.append((safe_name, data, dimensions[0], dimensions[1]))

    for name, data, image_width, image_height in photo_pages:
        image_id = len(objects) + 1
        objects.append(
            f'<< /Type /XObject /Subtype /Image /Width {image_width} /Height {image_height} '
            f'/ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /DCTDecode /Length {len(data)} >>\nstream\n'.encode()
            + data + b'\nendstream'
        )
        page_id = len(objects) + 1
        stream_id = page_id + 1
        max_width, max_height = 532, 690
        scale = min(max_width / image_width, max_height / image_height)
        draw_width, draw_height = image_width * scale, image_height * scale
        x, y = (612 - draw_width) / 2, 760 - draw_height
        safe_title = name.replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')[:100]
        commands = (
            f'BT /F1 12 Tf 40 800 Td ({safe_title}) Tj ET\n'
            f'q {draw_width:.2f} 0 0 {draw_height:.2f} {x:.2f} {y:.2f} cm /Im1 Do Q'
        ).encode('latin-1', 'replace')
        objects.append(
            f'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 842] '
            f'/Resources << /Font << /F1 3 0 R >> /XObject << /Im1 {image_id} 0 R >> >> '
            f'/Contents {stream_id} 0 R >>'.encode()
        )
        objects.append(b'<< /Length ' + str(len(commands)).encode() + b' >>\nstream\n' + commands + b'\nendstream')
        page_ids.append(page_id)
    names = ''
    if embedded_names:
        names = ' /Names << /EmbeddedFiles << /Names [' + ' '.join(embedded_names) + '] >> >>'
    objects[0] = f'<< /Type /Catalog /Pages 2 0 R{names} >>'.encode()
    pdf = bytearray(b'%PDF-1.4\n')
    offsets = [0]
    for index, obj in enumerate(objects, 1):
        offsets.append(len(pdf))
        pdf.extend(f'{index} 0 obj\n'.encode() + obj + b'\nendobj\n')
    xref_offset = len(pdf)
    pdf.extend(f'xref\n0 {len(offsets)}\n0000000000 65535 f \n'.encode())
    for offset in offsets[1:]:
        pdf.extend(f'{offset:010d} 00000 n \n'.encode())
    pdf.extend(f'trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF'.encode())
    return bytes(pdf)


def _jpeg_dimensions(data):
    """Return a JPEG's pixel dimensions, or None for malformed/non-JPEG data."""
    if not data.startswith(b'\xff\xd8'):
        return None
    index = 2
    while index + 4 <= len(data):
        if data[index] != 0xFF:
            index += 1
            continue
        marker = data[index + 1]
        index += 2
        if marker in {0xD8, 0xD9} or 0xD0 <= marker <= 0xD7:
            continue
        if index + 2 > len(data):
            return None
        segment_length = int.from_bytes(data[index:index + 2], 'big')
        if segment_length < 2 or index + segment_length > len(data):
            return None
        if marker in {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF}:
            if segment_length < 7:
                return None
            height = int.from_bytes(data[index + 3:index + 5], 'big')
            width = int.from_bytes(data[index + 5:index + 7], 'big')
            return (width, height) if width and height else None
        index += segment_length
    return None
