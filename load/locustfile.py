"""Locust load test for the ARKCafe / Crimson NCR project.

Why not Postman: the Postman Runner / Newman replay requests one at a time and report a
single response time per request. There is no concurrency, no RPS, no percentile
distribution and no pass/fail threshold, so it cannot measure load. Locust drives many
concurrent virtual users against the same read paths the Postman journeys exercise.

Usage
-----
    cd C:/Users/mycha/ARKCafe_SAD
    venv\\Scripts\\python.exe -m locust -f load/locustfile.py --host http://127.0.0.1:8000

Headless run (no browser UI):

    venv\\Scripts\\python.exe -m locust -f load/locustfile.py \\
        --host http://127.0.0.1:8000 --headless -u 20 -r 5 -t 60s \\
        --csv load/results/run1 --only-summary

Read-only run (excludes the tasks that create NCRs):

    ... --headless -u 20 -r 5 -t 60s --exclude-tags write

See load/README.md for environment variables, what to measure, and the caveats of
testing against `runserver` + SQLite.
"""
import os
import re

from locust import HttpUser, between, tag, task

BASE_URL = os.environ.get("ARKCAFE_BASE_URL", "http://127.0.0.1:8000")
ADMIN_EMAIL = os.environ.get("ARKCAFE_ADMIN_EMAIL", "admin@test.com")
ADMIN_PASSWORD = os.environ.get("ARKCAFE_ADMIN_PASSWORD", "Passw0rd!123")
STAFF_EMAIL = os.environ.get("ARKCAFE_STAFF_EMAIL", "staff@test.com")
STAFF_PASSWORD = os.environ.get("ARKCAFE_STAFF_PASSWORD", "Passw0rd!123")

# Creating NCRs writes rows that nothing deletes, so it is opt-in.
ALLOW_WRITES = os.environ.get("ARKCAFE_ALLOW_WRITES") == "1"

NCR_ID_RE = re.compile(r"/staff-records/(\d+)/")
OPTION_ID_RE = re.compile(r'<option value="(\d+)"')


class CrimsonUser(HttpUser):
    """Shared Django session + CSRF handling for every virtual user."""

    abstract = True
    host = BASE_URL
    wait_time = between(1, 3)

    email = ""
    password = ""

    def on_start(self):
        self.ncr_ids = []
        self.project_ids = []
        self.department_ids = []
        self.login()
        self.discover_ids()

    # ------------------------------------------------------------------ helpers
    def csrf_headers(self):
        """Django rotates the CSRF token on login, so read it from the jar each time."""
        token = self.client.cookies.get("csrftoken") or ""
        return {"X-CSRFToken": token, "Referer": self.host + "/login/"}

    def login(self):
        with self.client.get("/login/", name="/login/ [GET]", catch_response=True) as response:
            if response.status_code not in (200, 302):
                response.failure("login page returned %s" % response.status_code)
                return

        with self.client.post(
            "/login/",
            data={"username": self.email, "password": self.password},
            headers=self.csrf_headers(),
            allow_redirects=False,
            name="/login/ [POST]",
            catch_response=True,
        ) as response:
            if response.status_code != 302:
                response.failure("login failed with %s" % response.status_code)
            elif not self.client.cookies.get("sessionid"):
                response.failure("no session cookie issued")

    def discover_ids(self):
        """Pick up record and form-select IDs the same way the Postman journeys do."""
        response = self.client.get("/staff-records/", name="/staff-records/ [discover]")
        if response.status_code != 200:
            return
        body = response.text
        seen = []
        for match in NCR_ID_RE.finditer(body):
            if match.group(1) not in seen:
                seen.append(match.group(1))
        self.ncr_ids = seen[:20]

        for field, bucket in (("project", self.project_ids), ("department", self.department_ids)):
            block = re.search(r'name="%s"[\s\S]*?</select>' % field, body)
            if not block:
                continue
            for match in OPTION_ID_RE.finditer(block.group(0)):
                if match.group(1) not in bucket:
                    bucket.append(match.group(1))


class StaffUser(CrimsonUser):
    """QA/QC staff: the read-heavy paths, plus an optional NCR create."""

    weight = 4
    email = STAFF_EMAIL
    password = STAFF_PASSWORD

    @task(5)
    def records_list(self):
        self.client.get("/staff-records/", name="/staff-records/")

    @task(4)
    def records_filtered(self):
        self.client.get(
            "/staff-records/?status=open&q=NCR",
            name="/staff-records/?status,q",
        )

    @task(3)
    def ncr_detail(self):
        if not self.ncr_ids:
            self.client.get("/staff-records/", name="/staff-records/ [detail fallback]")
            return
        ncr_id = self.ncr_ids[0]
        response = self.client.get("/staff-records/%s/" % ncr_id, name="/staff-records/:id/")
        if response.status_code == 404:
            self.ncr_ids.pop(0)

    @task(2)
    def dashboard(self):
        self.client.get("/staff/dashboard/", name="/staff/dashboard/")

    @task(1)
    def audit_history(self):
        self.client.get("/staff/audit-history/", name="/staff/audit-history/")

    @task(1)
    def export_excel(self):
        """Realistic export: a spreadsheet build plus a full table scan."""
        self.client.post(
            "/staff/export/",
            data=[("export_type", "excel"), ("columns", "reference_no"),
                  ("columns", "subject"), ("columns", "status")],
            headers=self.csrf_headers(),
            name="/staff/export/ [POST xlsx]",
        )

    @task(1)
    def export_filtered_records(self):
        self.client.get(
            "/staff-records/?date_from=2026-01-01&date_to=2026-12-31",
            name="/staff-records/?date range",
        )

    @tag("write")
    @task(1)
    def create_ncr(self):
        if not ALLOW_WRITES:
            return
        if not self.project_ids or not self.department_ids:
            return
        with self.client.post(
            "/staff-create/",
            data={
                "project": self.project_ids[0],
                "department": self.department_ids[0],
                "package_no": "LOAD",
                "cause": "workmanship",
                "subject": "Load test NCR",
                "issued_date": "2026-01-20",
                "required_date": "2026-02-20",
                "description": "created by the Locust load test",
            },
            headers=self.csrf_headers(),
            allow_redirects=False,
            name="/staff-create/ [POST]",
            catch_response=True,
        ) as response:
            if response.status_code != 302:
                response.failure("create returned %s" % response.status_code)
            else:
                match = NCR_ID_RE.search(response.headers.get("Location", ""))
                if match:
                    self.ncr_ids.insert(0, match.group(1))


class AdminUser(CrimsonUser):
    """Admin: dashboards and the admin list views."""

    weight = 1
    email = ADMIN_EMAIL
    password = ADMIN_PASSWORD

    @task(3)
    def admin_dashboard(self):
        self.client.get("/reports/admin/dashboard/", name="/reports/admin/dashboard/")

    @task(2)
    def admin_projects(self):
        self.client.get("/admin-projects/", name="/admin-projects/")

    @task(2)
    def admin_departments(self):
        self.client.get("/admin-departments/", name="/admin-departments/")

    @task(1)
    def admin_users(self):
        self.client.get("/admin-users/", name="/admin-users/")

    @task(1)
    def admin_audit(self):
        self.client.get("/reports/admin/audit-history/", name="/reports/admin/audit-history/")

    @task(1)
    def active_ncr_dashboard(self):
        self.client.get(
            "/reports/admin/dashboard/?time_filter=custom&start_date=2026-01-01&end_date=2026-12-31",
            name="/reports/admin/dashboard/ [custom range]",
        )
