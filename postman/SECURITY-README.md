# ARKCafe NCR — Security Testing

Two complementary suites:

| Suite | File | Covers |
|---|---|---|
| Black-box HTTP | `ARKCafe-Security.postman_collection.json` (+ `gen_security.py`) | headers, cookies, CSRF, auth, role isolation, injection, method tampering |
| Django/CI | `../tests/test_security.py` | uploads, attachment access control, session fixation, write-verb safety, audit trail |

Run the Django suite (no Postman needed, safe for CI):

```powershell
cd C:\Users\mycha\ARKCafe_SAD
venv\Scripts\python.exe manage.py test tests -v 2
```

It creates and destroys its own test database — the dev `db.sqlite3` is untouched.

## The Postman collection

66 requests in 7 folders. Import it and select environment **ARKCafe - Local Dev**.

Every folder starts with **0a. GET /login/** + **0b. POST /logout/**, and every login step asserts
**which dashboard it landed on**. That is not decoration — `accounts/views.py` sets
`redirect_authenticated_user = True`, so `POST /login/` while a session is already live does **not**
switch accounts: it just redirects to the current user's dashboard. Without those guards a leftover
session makes every "staff cannot X" check silently test the wrong user (that produced a wave of
spurious `403` results during development).

| Folder | What it proves |
|---|---|
| 1. Transport & browser-security headers | `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, `Referrer-Policy`, no `X-Powered-By`, `csrftoken` is `SameSite=Lax`, headers survive redirects |
| 2. Authentication & session integrity | wrong password → no session; identical error for unknown email (no user enumeration); CSRF token rotated at login; `sessionid` is `HttpOnly` + `SameSite`; `GET /logout/` → 405 |
| 3. CSRF enforcement | `POST /login/` and `POST /admin-projects/add/` refused (403) with no token and with a forged token, even with a valid admin session; the blocked writes created nothing |
| 4. Authorization (vertical + horizontal) | anonymous → login redirect; staff blocked from admin pages, project create and **user create** (privilege escalation); admin blocked from every staff page |
| 5. Injection & input validation | SQL/stacked-SQL injection in `q` and filter params does not 500 or leak errors; malformed dates tolerated; reflected **and stored** XSS escaped (checked as "escaped **and** present", so a dropped payload cannot pass) |
| 6. Method tampering & state safety | `PUT`/`PATCH`/`DELETE` on POST-only endpoints → 405; `DELETE` on NCR detail changes nothing (verified by re-reading the status) |
| 7. Hardening gaps | **expected to fail** — see below |

**Folders 1–6 must be green.** Folder 7 asserts behaviour the app does not have yet, so it is
deliberately red until someone hardens it (**3 failures**: CSP, `no-store` cache headers and login
throttling). Run folders 1–6 only when you want a clean pass:

1. Open the collection → **Run** → uncheck folder 7 → Run.

Inside folder 7 the six failed-login steps run **signed out** on purpose: while a session is live,
`LoginView` never validates the password at all, so an "attempt" against a live session tests
nothing.

### Findings from the audit (what folder 7 is about)

| Gap | Evidence | Fix |
|---|---|---|
| No `Content-Security-Policy` | header absent on every response | Django 6.1 already supports it: add `django.middleware.csp.ContentSecurityPolicyMiddleware` to `MIDDLEWARE` and a `SECURE_CSP` dict to settings. Templates use inline `<script>` blocks and `style=""` attributes, so `'unsafe-inline'` is needed until they move to nonces |
| Authenticated pages are cacheable | `/staff-records/` returns **no** `Cache-Control` | add `no-store` for authenticated responses (middleware or `@never_cache`) — NCR data is sensitive |
| No login throttling | 7 consecutive bad passwords → 7 × `200`, never 429 | add `django-axes`, or a simple per-IP/user attempt counter |
| `DEBUG=True` in dev settings | `config/settings.py` defaults `DEBUG` to `"True"` | fine locally; make sure the deployed env sets `DEBUG=False` |
| Weak default `SECRET_KEY` | falls back to `"dev-only-key"` | set `SECRET_KEY` in the environment (see `manage.py check --deploy`) |
| Duplicate auth decorator | `administration/project_views.py` has its own `admin_required` raising **403**, while `core/decorators.admin_required` redirects **302** | delete the local copy and import from `core.decorators` |
| `DELETE` on NCR detail returns 200 | `ncr_detail` only branches on `POST` | add `@require_http_methods(["GET", "POST"])`; no data risk today |
| User-management POST is only role-guarded | `/admin-users/` actions rely on `admin_required` alone | verify `action` values against an allow-list (they partly do) and add CSRF tests for each action |

Deployment hardening check:

```powershell
venv\Scripts\python.exe manage.py check --deploy
```

Current output: 1 error (`mail.E001`, console email backend) and 6 warnings
(`SECURE_HSTS_SECONDS`, `SECURE_SSL_REDIRECT`, `SECRET_KEY`, `SESSION_COOKIE_SECURE`,
`CSRF_COOKIE_SECURE`, `DEBUG`). All six are expected for a dev config — they become real
requirements once this is deployed behind HTTPS.

## What this collection does NOT cover

- TLS/certificate configuration and HSTS (needs HTTPS; the dev server is HTTP).
- Dependency vulnerability scanning — use `pip-audit` in CI.
- Server configuration (gunicorn/nginx) — see `load/README.md`.
- Anything requiring a browser: clickjacking (only the header is checked), CSP behaviour,
  password-manager autofill, SPA/JS injection.

## Side effects

Folders 4 and 5 create NCR records (subjects `Security fixture NCR …` and `XSS …`). There is no
NCR delete endpoint, so they accumulate exactly like the E2E suite's records do. Nothing else is
created, modified or deleted — the collections never touch projects, departments or users.
