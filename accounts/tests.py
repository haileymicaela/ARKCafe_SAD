from django.test import TestCase
from django.urls import reverse

from .models import User


class LoginTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_user(
            "Admin@Example.com", "Ada Admin", "s3cret-pass!", role=User.ADMIN
        )
        cls.staff = User.objects.create_user("qa@example.com", "Quinn QA", "s3cret-pass!")
        cls.inactive = User.objects.create_user(
            "off@example.com", "Off User", "s3cret-pass!", is_active=False
        )
        cls.url = reverse("login")

    def test_login_page_renders(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "QA/QC NCR Tracking System")

    def test_email_is_stored_lowercase_and_hash_is_not_plaintext(self):
        self.assertEqual(self.admin.email, "admin@example.com")
        self.assertNotEqual(self.admin.password, "s3cret-pass!")

    def test_admin_redirects_to_admin_dashboard(self):
        response = self.client.post(
            self.url, {"username": "admin@example.com", "password": "s3cret-pass!"}
        )
        self.assertRedirects(response, reverse("admin_dashboard"))

    def test_login_email_is_case_insensitive(self):
        response = self.client.post(
            self.url, {"username": "ADMIN@example.com", "password": "s3cret-pass!"}
        )
        self.assertRedirects(response, reverse("admin_dashboard"))

    def test_staff_redirects_to_staff_dashboard(self):
        response = self.client.post(
            self.url, {"username": "qa@example.com", "password": "s3cret-pass!"}
        )
        self.assertRedirects(response, reverse("staff_dashboard"))

    def test_wrong_password_shows_error(self):
        response = self.client.post(
            self.url, {"username": "qa@example.com", "password": "nope"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Incorrect email or password.")

    def test_inactive_user_cannot_log_in(self):
        response = self.client.post(
            self.url, {"username": "off@example.com", "password": "s3cret-pass!"}
        )
        self.assertContains(response, "Incorrect email or password.")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_dashboards_require_login(self):
        response = self.client.get(reverse("staff_dashboard"))
        self.assertRedirects(
            response, f"{reverse('login')}?next={reverse('staff_dashboard')}"
        )

    def test_logout_requires_post_and_returns_to_login(self):
        self.client.force_login(self.staff)
        response = self.client.post(reverse("logout"))
        self.assertRedirects(response, reverse("login"))
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_staff_cannot_open_admin_pages(self):
        self.client.force_login(self.staff)
        response = self.client.get(reverse("admin_dashboard"))
        self.assertRedirects(response, reverse("staff_dashboard"))

    def test_admin_cannot_open_staff_pages(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("staff_dashboard"))
        self.assertRedirects(response, reverse("admin_dashboard"))
