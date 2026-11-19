from django.test import TestCase, RequestFactory
from unittest.mock import patch, MagicMock
from datetime import date, timedelta
from .views import dashboard_view, audit_history_view, export_ncr_view
import csv
from io import StringIO

class ReportsAppTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    @patch('reports.views.NcrRecord')
    @patch('reports.views.User')
    @patch('reports.views.Project')
    def test_dashboard_view_logic(self, mock_project, mock_user, mock_ncr):
        # Setup fake DB returns
        mock_ncr.objects.all.return_value = mock_ncr.objects
        mock_ncr.objects.filter.return_value.count.return_value = 15
        mock_user.objects.filter.return_value.count.return_value = 10
        mock_project.objects.count.return_value = 3

        request = self.factory.get('/reports/staff/dashboard/')
        response = dashboard_view(request)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context_data['total_open'], 15)
        self.assertEqual(response.context_data['active_users'], 10)
        self.assertTrue(response.context_data['is_staff'])

    @patch('reports.views.AuditLog')
    def test_audit_history_pagination(self, mock_audit):
        mock_queryset = MagicMock()
        mock_queryset.select_related.return_value.order_by.return_value = mock_queryset
        mock_queryset.filter.return_value = mock_queryset
        mock_queryset.count.return_value = 25 
        mock_queryset.__getitem__.side_effect = lambda x: list(range(10))
        mock_audit.objects = mock_queryset

        request = self.factory.get('/reports/staff/audit-history/', {'q': 'NCR-2026', 'page': 2})
        response = audit_history_view(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context_data['search_query'], 'NCR-2026')
        self.assertEqual(response.context_data['page_obj'].number, 2)

    @patch('reports.views.NcrRecord')
    def test_export_csv_view(self, mock_ncr):
        fake_ncr = MagicMock()
        fake_ncr.reference_no = "NCR-2026-001"
        fake_ncr.subject = "Cracked tiles"
        fake_ncr.project.project_name = "Solaire Resort"
        fake_ncr.get_cause_display.return_value = "Workmanship"
        fake_ncr.get_status_display.return_value = "Open"
        fake_ncr.issued_date = date.today()

        mock_ncr.objects.all.return_value = [fake_ncr]

        request = self.factory.post('/reports/staff/export/', {'export_type': 'excel'})
        response = export_ncr_view(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv')
        
        content = response.content.decode('utf-8')
        csv_reader = csv.reader(StringIO(content))
        rows = list(csv_reader)
        self.assertEqual(rows[0], ['NCR No', 'Subject', 'Project', 'Cause', 'Status', 'Date Raised'])
        self.assertEqual(rows[1][0], 'NCR-2026-001')