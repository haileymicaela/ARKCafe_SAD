from django.test import TestCase

# Create your tests here.

from django.conf import settings
from django.contrib.auth import get_user_model
from django.shortcuts import resolve_url
from django.test import Client, TestCase
from django.urls import reverse

User = get_user_model()
PASSWORD = "Str0ng-Pass!234"


def make_user(**extra):
    data = {"email": "staff@example.com", "password": PASSWORD}

    if User.USERNAME_FIELD != "email":
        data[User.USERNAME_FIELD] = "staff"

    data.update(extra)
    return User.objects.create_user(**data)


class LoginTests(TestCase):
    def setUp(self):
        self.url = reverse("login")
        self.user = make_user()
        self.dashboard = resolve_url(settings.LOGIN_REDIRECT_URL)

    def post(self, email="staff@example.com", password=PASSWORD, **extra):
        return self.client.post(
            self.url,
            {"username": email, "password": password, **extra}
        )

    def test_login_page_renders(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/login.html")
        self.assertContains(response, 'type="email"')
        self.assertContains(response, 'type="password"')

    def test_page_has_show_hide_password_toggle(self):
        self.assertContains(self.client.get(self.url), 'id="toggle-password"')

    def test_valid_login_redirects_to_dashboard(self):
        response = self.post()
        self.assertRedirects(
            response, self.dashboard, fetch_redirect_response=False
        )
        self.assertEqual(
            int(self.client.session["_auth_user_id"]), self.user.pk
        )

    def test_email_is_case_insensitive(self):
        response = self.post(email="STAFF@Example.com")
        self.assertRedirects(
            response, self.dashboard, fetch_redirect_response=False
        )

    def test_safe_next_url_is_followed(self):
        response = self.post(next="/some/page/")
        self.assertRedirects(
            response, "/some/page/", fetch_redirect_response=False
        )

    def test_external_next_url_is_ignored(self):
        response = self.post(next="https://evil.example.com/")
        self.assertRedirects(
            response, self.dashboard, fetch_redirect_response=False
        )

    def test_logged_in_user_is_redirected_away_from_login(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertRedirects(
            response, self.dashboard, fetch_redirect_response=False
        )

    def test_wrong_password_shows_error(self):
        response = self.post(password="wrong-password")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Incorrect email or password")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_unknown_email_shows_error(self):
        response = self.post(email="nobody@example.com")
        self.assertContains(response, "Incorrect email or password")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_inactive_user_cannot_log_in(self):
        make_user(
            email="off@example.com",
            is_active=False,
            **(
                {}
                if User.USERNAME_FIELD == "email"
                else {User.USERNAME_FIELD: "off"}
            )
        )

        response = self.post(email="off@example.com")
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_empty_submission_shows_error(self):
        response = self.client.post(self.url, {})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'role="alert"')

    def test_entered_email_is_kept_after_failed_login(self):
        response = self.post(password="wrong-password")
        self.assertContains(response, 'value="staff@example.com"')

    def test_password_is_not_echoed_back(self):
        response = self.post(password="wrong-password")
        self.assertNotContains(response, "wrong-password")

    def test_csrf_is_enforced(self):
        client = Client(enforce_csrf_checks=True)
        response = client.post(
            self.url,
            {"username": "staff@example.com", "password": PASSWORD}
        )
        self.assertEqual(response.status_code, 403)
