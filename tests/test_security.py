"""Security test suite for the ARKCafe / Crimson NCR project.

Covers the checks that need fixtures or database inspection, which a black-box
Postman run cannot do: file-upload validation, attachment access control,
session fixation, write-verb safety and audit-trail integrity.

Run:  venv\\Scripts\\python.exe manage.py test tests -v 2

The HTTP-level angles (security headers, CSRF enforcement, open redirect,
SQL/HTML injection, role isolation) are covered black-box by
postman/ARKCafe-Security.postman_collection.json.
"""
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase

from accounts.models import User
from core.models import Attachment, AuditLog, Department, NcrRecord, Project


class SecurityTestCase(TestCase):
    """Shared fixtures: an admin, a staff user, a project and a department."""

    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_user(
            email="sec-admin@test.com", password="Passw0rd!123", role="admin",
            full_name="Sec Admin",
        )
        cls.staff = User.objects.create_user(
            email="sec-staff@test.com", password="Passw0rd!123", role="staff",
            full_name="Sec Staff",
        )
        cls.project = Project.objects.create(
            project_name="Sec Project", client_name="Sec Client", project_code="SEC-001",
        )
        cls.department = Department.objects.create(department_name="Sec Department")

    # ---------------------------------------------------------------- helpers
    def login(self, email, password="Passw0rd!123"):
        self.client.post("/login/", {"username": email, "password": password})
        return self.client

    def staff_client(self):
        return self.login(self.staff.email)

    def admin_client(self):
        return self.login(self.admin.email)

    def ncr_payload(self, **overrides):
        data = {
            "project": self.project.pk,
            "department": self.department.pk,
            "package_no": "PKG-SEC",
            "cause": "workmanship",
            "subject": "Security test NCR",
            "issued_date": "2026-01-20",
            "required_date": "2026-02-20",
            "description": "created by tests",
        }
        data.update(overrides)
        return data

    def make_ncr(self, **overrides):
        return NcrRecord.objects.create(
            project=self.project, department=self.department, created_by=self.staff,
            reference_no=overrides.pop("reference_no", "NCR-2026-9001"),
            package_no="PKG-SEC", subject="Security test NCR", cause="workmanship",
            **overrides,
        )


class FileUploadSecurityTests(SecurityTestCase):
    """NcrForm.clean_attachments must reject dangerous or oversized uploads."""

    def test_rejects_executable_upload(self):
        self.staff_client()
        payload = self.ncr_payload(attachments=[
            SimpleUploadedFile("payload.exe", b"MZ\x90\x00", content_type="application/octet-stream")
        ])
        response = self.client.post("/staff-create/", payload)
        self.assertEqual(response.status_code, 200, "the form must re-render, not save")
        self.assertContains(response, "not an allowed file type")
        self.assertEqual(NcrRecord.objects.count(), 0)

    def test_rejects_oversized_upload(self):
        self.staff_client()
        big = SimpleUploadedFile("big.pdf", b"x" * (6 * 1024 * 1024), content_type="application/pdf")
        response = self.client.post("/staff-create/", self.ncr_payload(attachments=[big]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "larger than 5 MB")
        self.assertEqual(NcrRecord.objects.count(), 0)

    def test_rejects_too_many_files(self):
        self.staff_client()
        files = [SimpleUploadedFile("f%d.pdf" % i, b"x") for i in range(16)]
        response = self.client.post("/staff-create/", self.ncr_payload(attachments=files))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "at most 15")
        self.assertEqual(NcrRecord.objects.count(), 0)

    def test_accepts_allowed_pdf(self):
        self.staff_client()
        good = SimpleUploadedFile("evidence.pdf", b"%PDF-1.4 ok", content_type="application/pdf")
        response = self.client.post("/staff-create/", self.ncr_payload(attachments=[good]))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(NcrRecord.objects.count(), 1)
        self.assertEqual(Attachment.objects.count(), 1)


class AttachmentAccessControlTests(SecurityTestCase):
    """Attachment downloads are staff-only and bound to their own NCR."""

    def setUp(self):
        self.ncr = self.make_ncr()
        self.other = self.make_ncr(reference_no="NCR-2026-9002")
        self.attachment = Attachment.objects.create(
            ncr=self.ncr, file_name="../../etc/passwd.pdf",
            file_type="application/pdf", file_data=b"%PDF-1.4 test",
        )

    def test_anonymous_download_redirected_to_login(self):
        response = Client().get(
            "/staff-records/%s/attachments/%s/" % (self.ncr.pk, self.attachment.pk)
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response["Location"])

    def test_admin_cannot_download_staff_attachment(self):
        self.admin_client()
        response = self.client.get(
            "/staff-records/%s/attachments/%s/" % (self.ncr.pk, self.attachment.pk)
        )
        self.assertEqual(response.status_code, 302)

    def test_download_requires_matching_ncr(self):
        """Horizontal access: the attachment id alone must not be enough."""
        self.staff_client()
        response = self.client.get(
            "/staff-records/%s/attachments/%s/" % (self.other.pk, self.attachment.pk)
        )
        self.assertEqual(response.status_code, 404)

    def test_download_headers_prevent_content_sniffing(self):
        self.staff_client()
        response = self.client.get(
            "/staff-records/%s/attachments/%s/" % (self.ncr.pk, self.attachment.pk)
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["X-Content-Type-Options"], "nosniff")
        self.assertIn("attachment", response["Content-Disposition"])

    def test_path_traversal_in_filename_is_stripped(self):
        """A stored '../..' name must not become a path in Content-Disposition."""
        self.staff_client()
        response = self.client.get(
            "/staff-records/%s/attachments/%s/" % (self.ncr.pk, self.attachment.pk)
        )
        disposition = response["Content-Disposition"]
        self.assertIn('filename="passwd.pdf"', disposition)
        self.assertNotIn("..", disposition)

    def test_attachment_delete_requires_post(self):
        self.staff_client()
        url = "/staff-records/%s/attachments/%s/delete/" % (self.ncr.pk, self.attachment.pk)
        self.assertEqual(self.client.get(url).status_code, 405)
        self.assertTrue(Attachment.objects.filter(pk=self.attachment.pk).exists())


class SessionSecurityTests(SecurityTestCase):
    """Session keys must not be fixable by an attacker."""

    def test_session_key_rotated_on_login(self):
        attacker_key = "attacker-known-session-key-123456"
        self.client.cookies["sessionid"] = attacker_key
        response = self.client.post(
            "/login/", {"username": self.staff.email, "password": "Passw0rd!123"}
        )
        self.assertEqual(response.status_code, 302)
        new_key = self.client.cookies.get("sessionid")
        self.assertIsNotNone(new_key, "login must issue a new session")
        self.assertNotEqual(new_key.value, attacker_key)

    def test_failed_login_creates_no_session(self):
        self.client.get("/login/")
        self.client.post("/login/", {"username": self.staff.email, "password": "nope-nope"})
        self.assertFalse(self.client.cookies.get("sessionid"))

    def test_login_error_does_not_reveal_account_existence(self):
        client = Client()
        client.get("/login/")
        unknown = client.post(
            "/login/", {"username": "ghost@nowhere.test", "password": "nope-nope"}
        ).content.decode()
        client2 = Client()
        client2.get("/login/")
        wrong = client2.post(
            "/login/", {"username": self.staff.email, "password": "nope-nope"}
        ).content.decode()
        marker = "Incorrect email or password."
        self.assertIn(marker, unknown)
        self.assertIn(marker, wrong)


class WriteVerbSafetyTests(SecurityTestCase):
    """Only the documented verb may change state."""

    def setUp(self):
        self.ncr = self.make_ncr(status=NcrRecord.STATUS_IN_PROGRESS)

    def test_delete_verb_does_not_change_ncr_status(self):
        self.staff_client()
        self.client.delete("/staff-records/%s/" % self.ncr.pk)
        self.ncr.refresh_from_db()
        self.assertEqual(self.ncr.status, NcrRecord.STATUS_IN_PROGRESS)
        self.assertTrue(NcrRecord.objects.filter(pk=self.ncr.pk).exists())

    def test_post_only_admin_views_reject_other_verbs(self):
        self.admin_client()
        for verb in ("put", "patch", "delete"):
            with self.subTest(verb=verb):
                response = getattr(self.client, verb)(
                    "/admin-projects/%s/edit/" % self.project.pk
                )
                self.assertEqual(response.status_code, 405)
        self.project.refresh_from_db()
        self.assertEqual(self.project.project_code, "SEC-001")

    def test_get_logout_is_not_allowed(self):
        self.staff_client()
        self.assertEqual(self.client.get("/logout/").status_code, 405)
        self.assertTrue(self.client.cookies.get("sessionid"))


class AuditTrailTests(SecurityTestCase):
    """Every status change must leave an audit trail (integrity requirement)."""

    def setUp(self):
        self.ncr = self.make_ncr()

    def test_status_change_writes_audit_log(self):
        self.staff_client()
        response = self.client.post(
            "/staff-records/%s/" % self.ncr.pk,
            {"new_status": "in_progress", "remarks": "started"},
        )
        self.assertEqual(response.status_code, 302)
        log = AuditLog.objects.filter(ncr=self.ncr).order_by("-history_id").first()
        self.assertIsNotNone(log)
        self.assertEqual(log.new_status, NcrRecord.STATUS_IN_PROGRESS)
        self.assertEqual(log.user_id, self.staff.pk)
        self.assertEqual(log.remarks, "started")

    def test_resolving_without_a_resolution_type_is_refused(self):
        self.staff_client()
        response = self.client.post(
            "/staff-records/%s/" % self.ncr.pk, {"new_status": "resolved", "remarks": "no type"}
        )
        self.assertEqual(response.status_code, 200)
        self.ncr.refresh_from_db()
        self.assertEqual(self.ncr.status, NcrRecord.STATUS_OPEN)
        self.assertFalse(AuditLog.objects.filter(ncr=self.ncr).exists())


class CredentialStorageTests(SecurityTestCase):
    """Passwords must be stored with a real hasher, never in the clear."""

    def test_password_is_hashed(self):
        user = User.objects.get(pk=self.staff.pk)
        self.assertTrue(
            user.password.startswith(("pbkdf2_", "argon2", "bcrypt", "scrypt")),
            "unexpected password hasher: %r" % user.password[:30],
        )
        self.assertNotIn("Passw0rd!123", user.password)

    def test_password_field_is_never_rendered_back(self):
        client = Client()
        client.get("/login/")
        body = client.post(
            "/login/", {"username": self.staff.email, "password": "secret-not-echoed-1"}
        ).content.decode()
        self.assertNotIn("secret-not-echoed-1", body)

