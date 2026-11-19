from django.test import TestCase

# Create your tests here.

from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from core.models import Department


class DepartmentPageTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            "admin@example.com", "Admin User", "pass12345", role=User.ADMIN
        )
        self.staff = User.objects.create_user(
            "staff@example.com", "Staff User", "pass12345", role=User.STAFF
        )
        self.url = reverse("admin_departments")
        self.client.force_login(self.admin)

    def test_staff_cannot_open_page(self):
        self.client.force_login(self.staff)
        response = self.client.get(self.url)
        self.assertRedirects(response, reverse("staff_dashboard"))

    def test_list_and_search(self):
        Department.objects.create(department_name="Operations")
        Department.objects.create(department_name="Procurement")
        response = self.client.get(self.url, {"q": "proc"})
        self.assertContains(response, "Procurement")
        self.assertNotContains(response, "Operations")

    def test_add_department(self):
        response = self.client.post(self.url, {"action": "add", "add-department_name": "Quality"})
        self.assertRedirects(response, self.url)
        self.assertTrue(Department.objects.filter(department_name="Quality").exists())

    def test_add_duplicate_name_is_rejected(self):
        Department.objects.create(department_name="Operations")
        response = self.client.post(self.url, {"action": "add", "add-department_name": "operations"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "already exists")
        self.assertEqual(Department.objects.count(), 1)

    def test_rename_department(self):
        dept = Department.objects.create(department_name="Ops")
        response = self.client.post(
            self.url,
            {"action": "rename", "department_id": dept.pk, "rename-department_name": "Operations"},
        )
        self.assertRedirects(response, self.url)
        dept.refresh_from_db()
        self.assertEqual(dept.department_name, "Operations")

    def test_rename_to_existing_name_is_rejected(self):
        Department.objects.create(department_name="Operations")
        dept = Department.objects.create(department_name="Ops")
        response = self.client.post(
            self.url,
            {"action": "rename", "department_id": dept.pk, "rename-department_name": "Operations"},
        )
        self.assertContains(response, "already exists")
        dept.refresh_from_db()
        self.assertEqual(dept.department_name, "Ops")