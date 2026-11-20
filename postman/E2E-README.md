# ARKCafe NCR — End-to-End Testing (Postman)

This replaces the full suite with **E2E only**: two complete user journeys.

Files:
- `ARKCafe-E2E.postman_collection.json` — 31 requests, 2 journeys
- `ARKCafe-E2E.postman_environment.json` — `baseUrl` + admin/staff credentials

(Old files `ARKCafe.postman_collection.json`, `ARKCafe.postman_environment.json`,
`README.md`, `tmp_gen/`, `gen_e2e.py`, `out.txt`, `err.txt` can be deleted.)

## Setup (once)

1. Start the dev server:
   ```
   cd C:/Users/mycha/ARKCafe_SAD
   python manage.py runserver
   ```
2. Seed test data (once) — admin + staff users, one project, one department:
   ```
   python manage.py shell -c "
   from core.models import Department, Project
   from accounts.models import User
   a, _ = User.objects.get_or_create(email='admin@test.com', defaults={'role':'admin','is_staff':True})
   s, _ = User.objects.get_or_create(email='staff@test.com', defaults={'role':'staff'})
   a.set_password('Passw0rd!123'); a.save()
   s.set_password('Passw0rd!123'); s.save()
   Department.objects.get_or_create(department_name='Test Department')
   Project.objects.get_or_create(project_code='TEST-001', defaults={'project_name':'Test Project','client_name':'Test Client'})
   print('seeded OK')
   "
   ```
   (Adjust if your User model requires more fields.)
3. In Postman: **Import** both files above, then select environment **ARKCafe - Local Dev**
   (top-right dropdown). Credentials are pre-filled with the seeded accounts.

## Run

- Right-click folder **Journey A - Admin** → *Run folder* → Run. All 16 steps must pass.
- Then right-click **Journey B - Staff (QA/QC)** → *Run folder* → Run. All 13 steps must pass.
- Or run the whole collection in one go — the order is safe (A logs out before B logs in).

Each journey starts with **0a. Open /login/** and **0b. Ensure signed out**: the login view has
`redirect_authenticated_user = True`, so `GET /login/` returns **302** (not 200) whenever a session
from an earlier run is still in the cookie jar. Those two steps clear that state so the “anonymous”
assertions in step 1 test what they claim to test. They tolerate 200/302 (and 403 when no CSRF
cookie exists yet) instead of failing.

Any step whose URL needs a captured ID (`{{projectId}}`, `{{departmentId}}`, `{{ncrId}}`, `{{ncrRef}}`)
carries an auto-generated pre-request guard: if an earlier step failed to capture the ID, the request
is **skipped** rather than sent to `/…//` and failing with a confusing 404.

## What each journey proves

Journey A (Admin): anonymous `/` → login page → admin login lands on admin dashboard →
dashboards render → admin can create a project and a department → both appear in the lists →
audit page accessible → created records are cleaned up (and verified gone from the lists) →
logout kills the session.

Journey B (Staff): login → staff dashboard → records page (captures project/department IDs) →
create NCR → auto reference `NCR-YYYY-NNNN` generated, status `Open` → transition
`in_progress` → `resolved` (with resolution type) → history logged → audit history page →
Excel export works → logout.

## What to check / how to read errors

In the runner's **Passing/Failing** summary, every step should be green. When a step fails,
open its **Test Results** and match the failing assertion:

| Failing assertion | Meaning | Likely cause |
|---|---|---|
| `Lands on login page` / any `200` expected | Server not reachable or route changed | Server not running; `baseUrl` wrong |
| `Redirected (302)` + `Sent to ... dashboard` | Login rejected | Wrong credentials in the environment; user role not `admin`/`staff` |
| `sessionid cookie issued` | Django didn't create a session | Auth backend issue; check Django console for errors |
| `Seed data available` | No project/department in DB | Run the seeding script |
| `NCR created (302)` | Form rejected | Missing seed data, or NCR form fields changed |
| `Status badge is Open` / `In Progress` / `Resolved` | Status transition broken (or reference/status badge markup changed) | `ALLOWED_TRANSITIONS` or `StatusUpdateForm` changed |
| `Sent back to ... list` / `Sent back to the same NCR detail` | POST succeeded but redirected somewhere unexpected — often a validation failure redirecting back to the form | form/view changed |
| `Project row found (matched by code)` / `Department row found (matched by name)` | Created row not found in the list **for this run's unique name/code** — search or list view broke | list template or `?q=` filter changed |
| `Project gone after deletion` / `Department gone after deletion` | Delete silently failed (redirect still returns 302) | PROTECT relation, or delete handler changed |
| `Audit row exists for this NCR` | Status changes not written to `AuditLog` | audit hook changed |
| `xlsx content type` / `PK zip signature` | Export broke or returned an empty/error body | Export view changed |
| `X-Export-Records` / `X-Export-Filename` | Export ran but exported nothing, or the filename/headers changed | Export view changed |

Each failure isolates the broken step of the journey — that's the point of E2E testing here.

## Notes

- Journeys create records with timestamp-unique names and delete them again (Journey A);
  Journey B leaves one test NCR per run (no delete endpoint for NCRs yet — intentional).
- Every POST sends `X-CSRFToken: {{csrfToken}}`, kept fresh by a collection-level script
  that mirrors the `csrftoken` cookie. Don't remove that script.
