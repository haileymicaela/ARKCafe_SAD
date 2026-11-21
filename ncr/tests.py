from unittest import mock

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from core.models import (
    ActivityLog, Attachment, AuditLog, Department, NcrRecord, Project, Recipient,
)


class NcrBase(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user("staff@example.com", "Staff User", "pass12345", role=User.STAFF)
        self.admin = User.objects.create_user("admin@example.com", "Admin User", "pass12345", role=User.ADMIN)
        self.dept = Department.objects.create(department_name="Quality")
        self.project = Project.objects.create(
            project_name="Tower A", client_name="ACME", project_code="PRJ-001"
        )
        Recipient.objects.create(name="Boss", mobile_number="09170000000", department=self.dept)
        self.client.force_login(self.staff)

    def make_ncr(self, **kw):
        data = dict(
            project=self.project, department=self.dept, created_by=self.staff,
            reference_no=f"NCR-2026-{NcrRecord.objects.count() + 1:04d}",
            subject="Cracked weld", cause="material",
        )
        data.update(kw)
        return NcrRecord.objects.create(**data)

    def form_data(self, **kw):
        data = {
            "project": self.project.pk, "department": self.dept.pk, "package_no": "PKG-1",
            "cause": "workmanship", "subject": "Bad paint", "description": "Peeling",
            "issued_date": "2026-11-19", "required_date": "2026-11-30",
        }
        data.update(kw)
        return data


class AccessTests(NcrBase):
    def test_anonymous_goes_to_login(self):
        self.client.logout()
        self.assertEqual(self.client.get(reverse("staff_records")).status_code, 302)

    def test_admin_is_sent_to_admin_dashboard(self):
        self.client.force_login(self.admin)
        resp = self.client.get(reverse("staff_records"))
        self.assertRedirects(resp, reverse("admin_dashboard"), fetch_redirect_response=False)

    def test_staff_can_open_pages(self):
        ncr = self.make_ncr()
        for name, args in [("staff_records", []), ("staff_create_ncr", []),
                           ("ncr_detail", [ncr.pk]), ("ncr_edit", [ncr.pk])]:
            self.assertEqual(self.client.get(reverse(name, args=args)).status_code, 200, name)


class RecordsTests(NcrBase):
    def test_search_and_filters(self):
        self.make_ncr(subject="Cracked weld", cause="material")
        self.make_ncr(subject="Wrong sequence", cause="sequencing", status="resolved")
        url = reverse("staff_records")
        self.assertContains(self.client.get(url, {"q": "weld"}), "Cracked weld")
        self.assertNotContains(self.client.get(url, {"q": "weld"}), "Wrong sequence")
        self.assertNotContains(self.client.get(url, {"status": "resolved"}), "Cracked weld")
        self.assertNotContains(self.client.get(url, {"cause": "material"}), "Wrong sequence")

    def test_pagination(self):
        for _ in range(12):
            self.make_ncr()
        resp = self.client.get(reverse("staff_records"))
        self.assertEqual(len(resp.context["page_obj"]), 10)


class CreateTests(NcrBase):
    def test_create_generates_reference_attachment_history_and_sms(self):
        upload = SimpleUploadedFile("photo.png", b"fakepng", content_type="image/png")
        with mock.patch("notifications.services.send_sms") as sms, self.captureOnCommitCallbacks(execute=True):
            resp = self.client.post(reverse("staff_create_ncr"), self.form_data(attachments=upload))
        ncr = NcrRecord.objects.get()
        self.assertRedirects(resp, reverse("ncr_detail", args=[ncr.pk]))
        self.assertEqual(ncr.reference_no, f"NCR-{timezone.localdate().year}-0001")
        self.assertEqual(ncr.status, "open")
        self.assertEqual(ncr.created_by, self.staff)
        self.assertEqual(Attachment.objects.filter(ncr=ncr).count(), 1)
        self.assertEqual(AuditLog.objects.filter(ncr=ncr, new_status="open").count(), 1)
        self.assertEqual(ActivityLog.objects.filter(action_type="create").count(), 1)
        sms.assert_called_once()
        number, text = sms.call_args[0]
        self.assertEqual(number, "+639170000000")
        self.assertIn("New NCR", text)
        self.assertIn("Bad paint", text)
        self.assertIn("Workmanship", text)

    def test_reference_number_increments(self):
        self.client.post(reverse("staff_create_ncr"), self.form_data())
        self.client.post(reverse("staff_create_ncr"), self.form_data(subject="Second"))
        refs = list(NcrRecord.objects.order_by("ncr_id").values_list("reference_no", flat=True))
        year = timezone.localdate().year
        self.assertEqual(refs, [f"NCR-{year}-0001", f"NCR-{year}-0002"])

    def test_bad_file_type_rejected(self):
        bad = SimpleUploadedFile("virus.exe", b"x")
        resp = self.client.post(reverse("staff_create_ncr"), self.form_data(attachments=bad))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "not an allowed file type")
        self.assertEqual(NcrRecord.objects.count(), 0)

    def test_required_date_before_issued_rejected(self):
        resp = self.client.post(
            reverse("staff_create_ncr"), self.form_data(required_date="2026-11-01")
        )
        self.assertContains(resp, "cannot be earlier")
        self.assertEqual(NcrRecord.objects.count(), 0)

    def test_cause_is_required_and_validated(self):
        resp = self.client.post(reverse("staff_create_ncr"), self.form_data(cause="bogus"))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(NcrRecord.objects.count(), 0)


class EditTests(NcrBase):
    def test_edit_updates_and_logs(self):
        ncr = self.make_ncr()
        resp = self.client.post(reverse("ncr_edit", args=[ncr.pk]), self.form_data(subject="New subject"))
        self.assertRedirects(resp, reverse("ncr_detail", args=[ncr.pk]))
        ncr.refresh_from_db()
        self.assertEqual(ncr.subject, "New subject")
        self.assertEqual(ActivityLog.objects.filter(action_type="update").count(), 1)

    def test_attachment_download_and_delete(self):
        ncr = self.make_ncr()
        att = Attachment.objects.create(
            ncr=ncr, file_name="a.pdf", file_type="application/pdf", file_data=b"%PDF-1"
        )
        resp = self.client.get(reverse("ncr_attachment", args=[ncr.pk, att.pk]))
        self.assertEqual(b"".join(resp.streaming_content), b"%PDF-1")
        self.assertIn("attachment", resp["Content-Disposition"])
        self.client.post(reverse("ncr_attachment_delete", args=[ncr.pk, att.pk]))
        self.assertEqual(Attachment.objects.count(), 0)


class StatusTests(NcrBase):
    def post_status(self, ncr, **data):
        return self.client.post(reverse("ncr_detail", args=[ncr.pk]), data)

    def test_open_to_in_progress_logs_history_and_sms(self):
        ncr = self.make_ncr()
        with mock.patch("notifications.services.send_sms") as sms, self.captureOnCommitCallbacks(execute=True):
            resp = self.post_status(ncr, new_status="in_progress", remarks="Started")
        self.assertRedirects(resp, reverse("ncr_detail", args=[ncr.pk]))
        ncr.refresh_from_db()
        self.assertEqual(ncr.status, "in_progress")
        entry = AuditLog.objects.get(ncr=ncr)
        self.assertEqual((entry.old_status, entry.new_status, entry.remarks), ("open", "in_progress", "Started"))
        self.assertEqual(ActivityLog.objects.filter(action_type="status_change").count(), 1)
        sms.assert_called_once()
        self.assertIn("In Progress", sms.call_args[0][1])
        self.assertIn("Remarks: Started", sms.call_args[0][1])

    def test_resolve_requires_resolution_type(self):
        ncr = self.make_ncr(status="in_progress")
        resp = self.post_status(ncr, new_status="resolved")
        self.assertContains(resp, "Choose how this NCR was resolved")
        ncr.refresh_from_db()
        self.assertEqual(ncr.status, "in_progress")

    def test_resolve_sets_resolution_and_date(self):
        ncr = self.make_ncr(status="in_progress")
        self.post_status(ncr, new_status="resolved", resolution_type="replaced", resolution_note="New part")
        ncr.refresh_from_db()
        self.assertEqual(ncr.status, "resolved")
        self.assertEqual(ncr.resolution_type, "replaced")
        self.assertEqual(ncr.resolve_date, timezone.localdate())

    def test_invalid_transition_rejected(self):
        ncr = self.make_ncr(status="resolved")
        resp = self.post_status(ncr, new_status="in_progress")
        self.assertEqual(resp.status_code, 200)
        ncr.refresh_from_db()
        self.assertEqual(ncr.status, "resolved")

    def test_reopen_clears_resolution(self):
        ncr = self.make_ncr(status="resolved", resolution_type="closed", resolve_date=timezone.localdate())
        self.post_status(ncr, new_status="open", remarks="Defect came back")
        ncr.refresh_from_db()
        self.assertEqual((ncr.status, ncr.resolution_type, ncr.resolve_date), ("open", "", None))
        self.assertIn("Reopened", AuditLog.objects.get(ncr=ncr).remarks)