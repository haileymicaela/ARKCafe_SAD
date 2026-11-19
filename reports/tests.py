from django.test import TestCase
from datetime import date
from accounts.models import User
from core.models import ActivityLog, Attachment, Department, Project, NcrRecord, AuditLog
from zipfile import ZipFile
from io import BytesIO

class ReportsAppTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user('qa@example.com', 'Quinn QA', 'pass12345')
        self.client.force_login(self.staff)

    def test_export_page_renders_for_staff(self):
        response = self.client.get('/staff/export/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Export Summary')
        self.assertContains(response, 'Single NCR (PDF)')
        self.assertNotContains(response, 'name="columns" value="reference_no" checked')
        self.assertNotContains(response, 'name="include_history" checked')

    def test_dashboard_view_logic(self):
        department = Department.objects.create(department_name='Dashboard QA')
        project = Project.objects.create(
            project_name='Dashboard Project', client_name='Client', project_code='DASH-001'
        )
        for index, status in enumerate((NcrRecord.STATUS_OPEN, NcrRecord.STATUS_RESOLVED), 1):
            NcrRecord.objects.create(
                project=project,
                created_by=self.staff,
                department=department,
                reference_no=f'NCR-DASH-{index}',
                subject=f'Dashboard issue {index}',
                cause=NcrRecord.CAUSE_MATERIAL,
                status=status,
            )
        response = self.client.get('/staff/dashboard/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['total_open'], 1)
        self.assertEqual(response.context['total_closed'], 1)
        self.assertTrue(response.context['is_staff'])
        self.assertEqual(response.context['cause_data'][0], {'cause': 'Material', 'open': 1, 'closed': 1})
        self.assertEqual(response.context['project_data'][0], {
            'project': 'Dashboard Project', 'open': 1, 'closed': 1,
        })
        self.assertContains(response, 'cause-chart-data')
        self.assertContains(response, 'dashboard_charts.js')

    def test_audit_history_pagination(self):
        department = Department.objects.create(department_name='Quality Assurance')
        project = Project.objects.create(
            project_name='Test Project', client_name='Test Client', project_code='TEST-001'
        )
        ncr = NcrRecord.objects.create(
            project=project,
            created_by=self.staff,
            department=department,
            reference_no='NCR-2026-001',
            subject='Test issue',
            cause=NcrRecord.CAUSE_WORKMANSHIP,
            status=NcrRecord.STATUS_OPEN,
        )
        AuditLog.objects.bulk_create([
            AuditLog(
                ncr=ncr,
                user=self.staff,
                old_status='',
                new_status=NcrRecord.STATUS_OPEN,
                remarks=f'Update {index}',
            )
            for index in range(25)
        ])

        response = self.client.get('/staff/audit-history/?q=NCR-2026&page=2')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['search_query'], 'NCR-2026')
        self.assertEqual(response.context['page_obj'].number, 2)
        self.assertContains(response, 'audit-mobile-view')

    def test_activity_log_filter_options_and_backend_filters(self):
        admin = User.objects.create_user(
            'admin@example.com', 'Ada Admin', 'pass12345', role=User.ADMIN,
        )
        self.client.force_login(admin)
        initial = self.client.get('/reports/admin/recent-activity/')
        self.assertEqual(initial.status_code, 200)
        self.assertContains(initial, 'data-filter-choice="create"')
        self.assertContains(initial, 'Created')
        for action in ('create', 'update', 'rename', 'delete', 'password_reset', 'activate', 'deactivate'):
            self.assertContains(initial, f'data-filter-choice="{action}"')
        self.assertContains(initial, 'data-filter-choice="project"')
        self.assertContains(initial, 'data-filter-choice="department"')
        self.assertContains(initial, 'data-filter-choice="recipient"')
        self.assertContains(initial, 'data-filter-choice="user"')
        self.assertContains(initial, 'activity-mobile-view')
        self.assertNotContains(initial, '<strong>Entity</strong>')
        self.assertNotContains(initial, '<strong>Action</strong>')
        action_order = ('create', 'update', 'rename', 'delete', 'password_reset', 'activate', 'deactivate')
        positions = [initial.content.index(f'data-filter-choice="{action}"'.encode()) for action in action_order]
        self.assertEqual(positions, sorted(positions))

        ActivityLog.objects.create(
            user=self.staff,
            action_type='create',
            entity_type='project',
            entity_id=1,
            entity_label='NCR-2026-001',
        )
        ActivityLog.objects.create(
            user=self.staff,
            action_type='updated',
            entity_type='project',
            entity_id=2,
            entity_label='NCR-2026-002',
        )
        ActivityLog.objects.create(
            user=self.staff,
            action_type='update',
            entity_type='project',
            entity_id=3,
            entity_label='NCR-2026-003',
        )
        filtered = self.client.get('/reports/admin/recent-activity/', {
            'entity': 'project', 'action': 'create',
        })
        self.assertEqual(filtered.status_code, 200)
        self.assertEqual(filtered.context['page_obj'].paginator.count, 1)
        self.assertEqual(filtered.context['entity_filter_label'], 'Project')
        self.assertEqual(filtered.context['action_filter_label'], 'Created')

        aliases = self.client.get('/reports/admin/recent-activity/', {
            'entity': 'project', 'action': 'update',
        })
        self.assertEqual(aliases.context['page_obj'].paginator.count, 2)

    def _create_export_ncr(self):
        department = Department.objects.create(department_name='QA Export')
        project = Project.objects.create(
            project_name='Solaire Resort', client_name='Client', project_code='SOL-001'
        )
        return NcrRecord.objects.create(
            project=project,
            created_by=self.staff,
            department=department,
            reference_no='NCR-2026-001',
            package_no='PKG-114',
            subject='Cracked tiles',
            cause=NcrRecord.CAUSE_WORKMANSHIP,
            status=NcrRecord.STATUS_OPEN,
            issued_date=date.today(),
        )

    def test_export_excel_generates_filtered_xlsx(self):
        self._create_export_ncr()
        response = self.client.post('/staff/export/', {
            'export_type': 'excel', 'project': '', 'cause': 'workmanship',
            'status': 'open', 'package_no': 'PKG-114',
            'columns': ['reference_no', 'subject', 'project', 'package_no'],
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        self.assertEqual(response['X-Export-Records'], '1')
        with ZipFile(BytesIO(response.content)) as workbook:
            sheet = workbook.read('xl/worksheets/sheet1.xml').decode()
        self.assertIn('NCR-2026-001', sheet)
        self.assertIn('Cracked tiles', sheet)
        self.assertIn('PKG-114', sheet)

    def test_export_pdf_generates_single_ncr_report(self):
        ncr = self._create_export_ncr()
        Attachment.objects.create(
            ncr=ncr,
            file_name='inspection-photo.jpg',
            file_type='image/jpeg',
            file_data=b'fake-image-data',
        )
        response = self.client.post('/staff/export/', {
            'export_type': 'pdf', 'single_ncr': ncr.pk,
            'include_attachments': 'on', 'include_history': 'on', 'include_resolution': 'on',
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertTrue(response.content.startswith(b'%PDF-1.4'))
        self.assertIn(b'NCR-2026-001', response.content)
        self.assertIn(b'inspection-photo.jpg', response.content)
        self.assertIn(b'fake-image-data', response.content)
