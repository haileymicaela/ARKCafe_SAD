from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from core.models import Department, NcrRecord, Project


class UserAccountsTests(TestCase):
    def setUp(self):
        self.dept = Department.objects.create(department_name="QA/QC")
        self.admin = User.objects.create_user(
            "admin@example.com", "Admin User", "pass12345", role=User.ADMIN, department=self.dept
        )
        self.staff = User.objects.create_user(
            "staff@example.com", "Staff User", "pass12345", role=User.STAFF, department=self.dept
        )
        self.url = reverse("admin_users")
        self.client.force_login(self.admin)

    def add_data(self, **overrides):
        data = {
            "action": "add",
            "add-full_name": "Katrina Lim",
            "add-email": "Katrina.Lim@Example.com",
            "add-department": self.dept.pk,
            "add-role": "staff",
            "add-password1": "temp12345",
            "add-password2": "temp12345",
        }
        data.update(overrides)
        return data

    def edit_data(self, user, **overrides):
        data = {
            "action": "edit",
            "user_id": user.pk,
            "edit-full_name": user.full_name,
            "edit-email": user.email,
            "edit-department": self.dept.pk,
            "edit-role": user.role,
            "edit-is_active": "1",
        }
        data.update(overrides)
        return data

    def test_staff_cannot_open_page(self):
        self.client.force_login(self.staff)
        self.assertRedirects(self.client.get(self.url), reverse("staff_dashboard"))

    def test_search_and_filters(self):
        response = self.client.get(self.url, {"q": "staff"})
        self.assertContains(response, "staff@example.com")
        self.assertNotContains(response, "admin@example.com")
        response = self.client.get(self.url, {"role": "admin"})
        self.assertContains(response, "admin@example.com")
        self.assertNotContains(response, "staff@example.com")

    def test_pagination_is_eight_per_page(self):
        for i in range(8):
            User.objects.create_user(f"u{i}@example.com", f"User {i}", "pass12345")
        response = self.client.get(self.url)
        self.assertEqual(len(response.context["page_obj"]), 8)
        self.assertEqual(response.context["page_obj"].paginator.count, 10)

    def test_add_user(self):
        response = self.client.post(self.url, self.add_data())
        self.assertRedirects(response, self.url)
        user = User.objects.get(email="katrina.lim@example.com")
        self.assertTrue(user.check_password("temp12345"))
        self.assertEqual(user.role, User.STAFF)

    def test_add_duplicate_email_case_insensitive(self):
        response = self.client.post(self.url, self.add_data(**{"add-email": "STAFF@example.com"}))
        self.assertContains(response, "already exists")
        self.assertEqual(User.objects.count(), 2)

    def test_add_password_mismatch(self):
        response = self.client.post(self.url, self.add_data(**{"add-password2": "different1"}))
        self.assertContains(response, "do not match")
        self.assertEqual(User.objects.count(), 2)

    def test_edit_user(self):
        response = self.client.post(
            self.url, self.edit_data(self.staff, **{"edit-full_name": "Renamed Staff", "edit-role": "admin"})
        )
        self.assertRedirects(response, self.url)
        self.staff.refresh_from_db()
        self.assertEqual(self.staff.full_name, "Renamed Staff")
        self.assertEqual(self.staff.role, User.ADMIN)

    def test_edit_to_existing_email_rejected(self):
        response = self.client.post(
            self.url, self.edit_data(self.staff, **{"edit-email": "admin@example.com"})
        )
        self.assertContains(response, "already exists")
        self.staff.refresh_from_db()
        self.assertEqual(self.staff.email, "staff@example.com")

    def test_edit_cannot_deactivate_or_demote_self(self):
        response = self.client.post(
            self.url, self.edit_data(self.admin, **{"edit-is_active": "0", "edit-role": "staff"})
        )
        self.assertContains(response, "own account")
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.is_active)
        self.assertEqual(self.admin.role, User.ADMIN)

    def test_deactivate(self):
        self.client.post(self.url, {"action": "deactivate", "user_id": self.staff.pk})
        self.staff.refresh_from_db()
        self.assertFalse(self.staff.is_active)

    def test_cannot_deactivate_self(self):
        self.client.post(self.url, {"action": "deactivate", "user_id": self.admin.pk})
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.is_active)

    def test_delete_user_without_records(self):
        self.client.post(self.url, {"action": "delete", "user_id": self.staff.pk})
        self.assertFalse(User.objects.filter(pk=self.staff.pk).exists())

    def test_delete_blocked_when_user_has_ncrs(self):
        project = Project.objects.create(project_name="P", client_name="C", project_code="P-1")
        NcrRecord.objects.create(
            project=project, created_by=self.staff, department=self.dept,
            reference_no="NCR-1", subject="Subject", cause="material",
        )
        self.client.post(self.url, {"action": "delete", "user_id": self.staff.pk})
        self.assertTrue(User.objects.filter(pk=self.staff.pk).exists())

    def test_cannot_delete_self(self):
        self.client.post(self.url, {"action": "delete", "user_id": self.admin.pk})
        self.assertTrue(User.objects.filter(pk=self.admin.pk).exists())

    def test_reset_password(self):
        response = self.client.post(
            self.url,
            {"action": "reset", "user_id": self.staff.pk,
             "reset-new_password1": "brandnew123", "reset-new_password2": "brandnew123"},
        )
        self.assertRedirects(response, self.url)
        self.staff.refresh_from_db()
        self.assertTrue(self.staff.check_password("brandnew123"))