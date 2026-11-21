# -*- coding: utf-8 -*-
"""Generator: ARKCafe-Security.postman_collection.json

Black-box security tests. Every assertion was verified against the running app,
including a step-by-step replay through ONE cookie jar (which is how Postman runs
a collection) - see the note on redirect_authenticated_user in clean_preamble().

Run:  python postman/gen_security.py
"""
import json, os

CSRF_HDR = {"key": "X-CSRFToken", "value": "{{csrfToken}}"}

GUARD_HEADER = "// Skip cleanly if an earlier step failed to capture an ID (avoids a 404 cascade)"
ID_VARS = ("projectId", "departmentId", "ncrId", "xssId")

# issued_date is auto-set to today by the server and rendered disabled, so a POSTed
# value is ignored. Hard-coded required_dates therefore rot: once "today" passes
# them the form rejects the post with 'Required date cannot be earlier than the
# issued date' and returns 200 instead of redirecting. Always compute from today.
DATE_PREREQ = (
    "// Dates must be relative to today - the server forces issued_date = today\n"
    "const _p=(n)=>String(n).padStart(2,'0');"
    "const _f=(d)=>d.getFullYear()+'-'+_p(d.getMonth()+1)+'-'+_p(d.getDate());"
    "const _n=new Date();"
    "pm.collectionVariables.set('issuedDate', _f(_n));"
    "pm.collectionVariables.set('requiredDate', _f(new Date(_n.getTime()+30*86400000)));"
)

ADMIN_DASH = r"/admin-dashboard|reports\/admin\/dashboard/"
STAFF_DASH = r"/staff-dashboard|staff\/dashboard/"


def guard_for(path):
    missing = [v for v in ID_VARS if "{{%s}}" % v in path]
    if not missing:
        return []
    cond = " || ".join("!pm.collectionVariables.get('%s')" % v for v in missing)
    return [
        GUARD_HEADER,
        "if (%s) {" % cond,
        "  if (pm.execution && pm.execution.skipRequest) { pm.execution.skipRequest(); }",
        "  else { postman.setNextRequest(null); }",
        "}",
    ]


def ue(pairs):
    return {"mode": "urlencoded", "urlencoded": [
        {"key": k, "value": v, "type": "text"} for k, v in pairs
    ]}


def item(name, method, path, tests=None, body=None, follow=True, headers=None, prereq=None, desc=None):
    it = {"name": name}
    events = []
    prereq = guard_for(path) + list(prereq or [])
    if prereq:
        events.append({"listen": "prerequest", "script": {"type": "text/javascript", "exec": prereq}})
    if tests:
        events.append({"listen": "test", "script": {"type": "text/javascript", "exec": tests}})
    if events:
        it["event"] = events
    req = {"method": method, "header": list(headers or [])}
    if desc:
        req["description"] = desc
    if not follow:
        it["protocolProfileBehavior"] = {"followRedirects": False}
    if body:
        req["body"] = body
    req["url"] = "{{baseUrl}}" + path
    it["request"] = req
    return it


def landed_on(regex, label):
    """Assert the login landed on THIS role's dashboard.

    accounts/views.py sets redirect_authenticated_user = True, so posting the login
    form while a session already exists does NOT switch accounts - it just redirects to
    the current user's dashboard. Without this assertion a stale session passes silently
    and every later "staff cannot X" / "admin cannot Y" check tests the wrong user.
    """
    return [
        "pm.test('Landed on the %s dashboard', () =>" % label,
        "  pm.expect(pm.response.headers.get('Location') || '').to.match(%s));" % regex,
    ]


def clean_preamble():
    """Guarantee an anonymous session before the steps that assume one."""
    return [
        item("0a. GET /login/ (fresh CSRF cookie, clear run state)", "GET", "/login/",
             prereq=[
                 "['projectId','departmentId','ncrId','xssId','csrfBefore','secUniq','xssUniq']",
                 "  .forEach(function(k){ pm.collectionVariables.unset(k); });",
             ],
             tests=["pm.test('Login route reachable', () => pm.expect([200, 302]).to.include(pm.response.code));"],
             desc="Also gives the next step a csrftoken cookie so POST /logout/ is not refused."),
        item("0b. POST /logout/ (ensure signed out)", "POST", "/logout/", headers=[CSRF_HDR], follow=False,
             tests=[
                 "pm.test('Sign-out attempted', () => pm.expect([200, 302, 403]).to.include(pm.response.code));",
                 "pm.test('No session cookie remains', () =>",
                 "  pm.expect(pm.cookies.get('sessionid') || '').to.eql(''));",
             ],
             desc="Clears any session left by an earlier run so the next steps really are anonymous."),
    ]


def login_step(name, email, password, role_regex, role_label, extra_tests=None):
    return item(name, "POST", "/login/", headers=[CSRF_HDR], follow=False,
                body=ue([("username", email), ("password", password)]),
                tests=[
                    "pm.test('Login accepted (302)', () => pm.expect(pm.response.code).to.eql(302));",
                    "pm.test('Session cookie issued', () => pm.expect(!!pm.cookies.get('sessionid')).to.be.true);",
                ] + landed_on(role_regex, role_label) + list(extra_tests or []))


def logout_step(name):
    return item(name, "POST", "/logout/", headers=[CSRF_HDR], follow=False,
                tests=["pm.test('Sign-out attempted', () => pm.expect([200, 302, 403]).to.include(pm.response.code));"])


collection = {
    "info": {
        "_postman_id": "a7c1d2e3-4444-4b7c-9d8e-9f0a1b2c3d4e",
        "name": "ARKCafe NCR - Security Tests",
        "description": (
            "Black-box security tests for the ARKCafe / Crimson NCR Django project.\n\n"
            "Folders:\n"
            "  1. Transport & browser-security headers\n"
            "  2. Authentication & session integrity\n"
            "  3. CSRF enforcement\n"
            "  4. Authorization (vertical + horizontal)\n"
            "  5. Injection & input validation\n"
            "  6. Method tampering & state safety\n\n"
            "All folders must be green.\n\n"
            "Every folder starts with 0a/0b (GET /login/ + POST /logout/) and every login step\n"
            "asserts WHICH dashboard it landed on. That is deliberate: accounts/views.py uses\n"
            "redirect_authenticated_user=True, so posting the login form while a session exists\n"
            "redirects instead of switching accounts - without those guards a leftover session\n"
            "makes the role-isolation checks test the wrong user.\n\n"
            "Folders 4-6 need the IDs captured in folder 4. Run the whole collection in order;\n"
            "steps whose ID is missing skip themselves instead of failing with a 404.\n\n"
            "Non-destructive except that folders 4 and 5 create NCR records (there is no NCR\n"
            "delete endpoint). No project, department or user is created or deleted.\n\n"
            "Prereqs: dev server on {{baseUrl}}, environment 'ARKCafe - Local Dev' selected,\n"
            "at least one Project and one Department in the DB."
        ),
        "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
    },
    "item": [],
    "variable": [
        {"key": "csrfToken", "value": "", "type": "string"},
        {"key": "csrfBefore", "value": "", "type": "string"},
        {"key": "projectId", "value": "", "type": "string"},
        {"key": "departmentId", "value": "", "type": "string"},
        {"key": "ncrId", "value": "", "type": "string"},
        {"key": "xssId", "value": "", "type": "string"},
        {"key": "xssPayload", "value": "<script>alert('xss')</script>", "type": "string"},
        {"key": "sqliPayload", "value": "' OR 1=1--", "type": "string"},
    ],
    "event": [{
        "listen": "test",
        "script": {"type": "text/javascript", "exec": [
            "// Keep the Django CSRF token in sync with the csrftoken cookie",
            "try {",
            "  const ck = pm.cookies.get('csrftoken');",
            "  if (ck) pm.collectionVariables.set('csrfToken', ck);",
            "} catch (e) { /* cookie jar not available */ }",
        ]},
    }],
}

# ---------------------------------------------------------------- 1. headers
sec_headers = clean_preamble() + [
    item("1. Login page sets browser-security headers", "GET", "/login/",
         tests=[
             "pm.test('Page served', () => pm.expect([200, 302]).to.include(pm.response.code));",
             "pm.test('X-Frame-Options: DENY (clickjacking)', () =>",
             "  pm.expect(pm.response.headers.get('X-Frame-Options')).to.eql('DENY'));",
             "pm.test('X-Content-Type-Options: nosniff (MIME sniffing)', () =>",
             "  pm.expect(pm.response.headers.get('X-Content-Type-Options')).to.eql('nosniff'));",
             "pm.test('Referrer-Policy is not missing', () =>",
             "  pm.expect(pm.response.headers.get('Referrer-Policy')).to.be.a('string'));",
             "pm.test('No X-Powered-By technology banner', () =>",
             "  pm.expect(pm.response.headers.get('X-Powered-By')).to.be.oneOf([null, undefined]));",
         ]),
    item("2. CSRF cookie is set with SameSite=Lax", "GET", "/login/",
         tests=[
             "pm.test('csrftoken cookie present', () =>",
             "  pm.expect(pm.cookies.get('csrftoken')).to.be.a('string'));",
             "pm.test('csrftoken is SameSite=Lax', () => {",
             "  const raw = pm.response.headers.get('Set-Cookie') || '';",
             "  pm.expect(raw.toLowerCase()).to.include('csrftoken');",
             "  pm.expect(raw.toLowerCase()).to.include('samesite=lax');",
             "});",
         ]),
    item("3. Protected page is not rendered to an anonymous client", "GET", "/admin-projects/",
         follow=False,
         tests=[
             "pm.test('Redirected, not served (302)', () => pm.expect(pm.response.code).to.eql(302));",
             "pm.test('Redirect target is the login page', () =>",
             "  pm.expect(pm.response.headers.get('Location') || '').to.include('/login/'));",
             "pm.test('No project data leaked in the redirect body', () =>",
             "  pm.expect(pm.response.text()).to.not.include('admin-projects/'));",
             "pm.test('Security headers still applied on the redirect', () =>",
             "  pm.expect(pm.response.headers.get('X-Frame-Options')).to.eql('DENY'));",
         ]),
]

# ---------------------------------------------------------------- 2. auth & session
sec_auth = clean_preamble() + [
    item("1. Wrong password: rejected, no session, no account oracle", "POST", "/login/",
         headers=[CSRF_HDR], follow=False,
         body=ue([("username", "{{staffEmail}}"), ("password", "wrong-password-123")]),
         tests=[
             "pm.test('Re-renders the form (200, no redirect)', () =>",
             "  pm.expect(pm.response.code).to.eql(200));",
             "pm.test('No session created', () => pm.expect(!!pm.cookies.get('sessionid')).to.be.false);",
             "pm.test('Generic error message', () =>",
             "  pm.expect(pm.response.text()).to.include('Incorrect email or password'));",
             "pm.test('Password is not echoed back into the page', () =>",
             "  pm.expect(pm.response.text()).to.not.include('wrong-password-123'));",
         ]),
    item("2. Unknown email gives the same error (no user enumeration)", "POST", "/login/",
         headers=[CSRF_HDR], follow=False,
         body=ue([("username", "ghost-user-{{$timestamp}}@nowhere.test"),
                  ("password", "wrong-password-123")]),
         tests=[
             "pm.test('Same generic message as a wrong password', () =>",
             "  pm.expect(pm.response.text()).to.include('Incorrect email or password'));",
             "pm.test('No session created', () => pm.expect(!!pm.cookies.get('sessionid')).to.be.false);",
         ],
         desc="Identical response for 'unknown user' and 'bad password' prevents account discovery."),
    item("3. Capture the CSRF token before login", "GET", "/login/",
         tests=[
             "const t = pm.cookies.get('csrftoken');",
             "if (t) pm.collectionVariables.set('csrfBefore', t);",
             "pm.test('Pre-login CSRF token captured', () => pm.expect(!!t).to.be.true);",
         ]),
    login_step("4. Staff login rotates the CSRF token and sets a hardened cookie",
               "{{staffEmail}}", "{{staffPassword}}", STAFF_DASH, "staff", extra_tests=[
                   "pm.test('CSRF token rotated on login', () => {",
                   "  const before = pm.collectionVariables.get('csrfBefore');",
                   "  const after = pm.cookies.get('csrftoken');",
                   "  pm.expect(after).to.be.a('string');",
                   "  pm.expect(after).to.not.eql(before);",
                   "});",
                   "pm.test('sessionid is HttpOnly', () => {",
                   "  const raw = (pm.response.headers.get('Set-Cookie') || '').toLowerCase();",
                   "  pm.expect(raw).to.include('sessionid');",
                   "  pm.expect(raw).to.include('httponly');",
                   "});",
                   "pm.test('sessionid is SameSite', () =>",
                   "  pm.expect((pm.response.headers.get('Set-Cookie') || '').toLowerCase()).to.include('samesite'));",
               ]),
    item("5. Logout cannot be triggered by GET (CSRF-free state change)", "GET", "/logout/", follow=False,
         tests=[
             "pm.test('Method Not Allowed (405)', () => pm.expect(pm.response.code).to.eql(405));",
             "pm.test('Session is still valid after the GET attempt', () => {",
             "  pm.expect(!!pm.cookies.get('sessionid')).to.be.true;",
             "});",
         ],
         desc="A GET-triggered logout would let any page log a user out (CSRF / nuisance attack)."),
]

# ---------------------------------------------------------------- 3. CSRF
sec_csrf = clean_preamble() + [
    item("1. POST /login/ with no CSRF token is refused", "POST", "/login/", follow=False,
         body=ue([("username", "{{staffEmail}}"), ("password", "{{staffPassword}}")]),
         tests=[
             "pm.test('Forbidden (403)', () => pm.expect(pm.response.code).to.eql(403));",
             "pm.test('Blocked by CSRF, not by credentials', () =>",
             "  pm.expect(pm.response.text().toLowerCase()).to.include('csrf'));",
             "pm.test('No session issued', () => pm.expect(pm.cookies.get('sessionid') || '').to.eql(''));",
         ],
         desc="No X-CSRFToken header and no csrfmiddlewaretoken field are sent."),
    item("2. POST /login/ with a forged CSRF token is refused", "POST", "/login/", follow=False,
         headers=[{"key": "X-CSRFToken", "value": "forged-token-value-0000000000000000"}],
         body=ue([("username", "{{staffEmail}}"), ("password", "{{staffPassword}}")]),
         tests=[
             "pm.test('Forbidden (403)', () => pm.expect(pm.response.code).to.eql(403));",
             "pm.test('No session issued', () => pm.expect(pm.cookies.get('sessionid') || '').to.eql(''));",
         ]),
    item("3. GET /login/ (fresh token for the admin session)", "GET", "/login/",
         tests=["pm.test('Login page reachable', () => pm.expect([200, 302]).to.include(pm.response.code));"]),
    login_step("4. POST login as ADMIN", "{{adminEmail}}", "{{adminPassword}}", ADMIN_DASH, "admin"),
    item("5. Admin write WITHOUT a CSRF token is refused", "POST", "/admin-projects/add/", follow=False,
         body=ue([("project_name", "CSRF Probe"), ("client_name", "CSRF Probe"),
                  ("project_code", "CSRF-NOTOKEN"), ("description", "must not be created")]),
         tests=[
             "pm.test('Forbidden (403)', () => pm.expect(pm.response.code).to.eql(403));",
             "pm.test('Not created (no 302 redirect)', () => pm.expect(pm.response.code).to.not.eql(302));",
         ],
         desc="A valid admin session alone must not be enough to mutate data."),
    item("6. Admin write with a forged CSRF token is refused", "POST", "/admin-projects/add/", follow=False,
         headers=[{"key": "X-CSRFToken", "value": "forged-token-value-0000000000000000"}],
         body=ue([("project_name", "CSRF Probe"), ("client_name", "CSRF Probe"),
                  ("project_code", "CSRF-FORGED"), ("description", "must not be created")]),
         tests=["pm.test('Forbidden (403)', () => pm.expect(pm.response.code).to.eql(403));"]),
    item("7. The CSRF-blocked writes created nothing", "GET", "/admin-projects/?q=CSRF-",
         tests=[
             "pm.test('List page renders (admin session is valid)', () =>",
             "  pm.expect(pm.response.code).to.eql(200));",
             "pm.test('It really is the project list, not a login redirect', () => {",
             "  const b = pm.response.text();",
             "  pm.expect(b).to.not.include('name=\"username\"');",
             "  pm.expect(b).to.include('admin-projects');",
             "});",
             "pm.test('No CSRF-NOTOKEN project exists', () =>",
             "  pm.expect(pm.response.text()).to.not.include('CSRF-NOTOKEN'));",
             "pm.test('No CSRF-FORGED project exists', () =>",
             "  pm.expect(pm.response.text()).to.not.include('CSRF-FORGED'));",
         ]),
]

# ---------------------------------------------------------------- 4. authorization
sec_authz = [
    logout_step("1. POST /logout/ (start anonymous)"),
    item("2. Anonymous access to the staff export endpoint is refused", "GET", "/staff/export/",
         follow=False,
         tests=[
             "pm.test('Redirected to login', () => pm.expect(pm.response.code).to.eql(302));",
             "pm.test('Location is the login page', () =>",
             "  pm.expect(pm.response.headers.get('Location') || '').to.include('/login/'));",
             "pm.test('No export body leaked', () =>",
             "  pm.expect(pm.response.text()).to.not.include('spreadsheetml'));",
         ]),
    login_step("3. POST login as STAFF", "{{staffEmail}}", "{{staffPassword}}", STAFF_DASH, "staff"),
    item("4. Staff cannot open the admin user-management page", "GET", "/admin-users/", follow=False,
         tests=[
             "pm.test('Not served (never 200)', () => pm.expect(pm.response.code).to.not.eql(200));",
             "pm.test('Redirected to the staff dashboard', () =>",
             "  pm.expect(pm.response.headers.get('Location') || '').to.include('staff'));",
         ]),
    item("5. Staff cannot list projects", "GET", "/admin-projects/", follow=False,
         tests=[
             "pm.test('Denied: 302 (core.decorators) or 403 (project_views)', () =>",
             "  pm.expect([302, 403]).to.include(pm.response.code));",
         ]),
    item("6. Staff cannot create a project (privilege escalation attempt)", "POST",
         "/admin-projects/add/", headers=[CSRF_HDR], follow=False,
         body=ue([("project_name", "Escalated"), ("client_name", "Escalated"),
                  ("project_code", "ESCALATED-1"), ("description", "must not be created")]),
         tests=[
             "pm.test('Not created (never 200)', () => pm.expect(pm.response.code).to.not.eql(200));",
             "pm.test('Denied with 403 or 302', () =>",
             "  pm.expect([302, 403]).to.include(pm.response.code));",
         ]),
    item("7. Staff cannot create an admin user", "POST", "/admin-users/", headers=[CSRF_HDR], follow=False,
         body=ue([("action", "add"), ("add-full_name", "Escalated User"),
                  ("add-email", "escalated@nowhere.test"), ("add-role", "admin"),
                  ("add-mobile_number", "09170000000")]),
         tests=[
             "pm.test('Not created (never 200)', () => pm.expect(pm.response.code).to.not.eql(200));",
             "pm.test('Denied with 403 or 302', () =>",
             "  pm.expect([302, 403]).to.include(pm.response.code));",
         ]),
    item("8. Staff create form exposes project/department IDs", "GET", "/staff-create/",
         tests=[
             "pm.test('Create form 200', () => pm.expect(pm.response.code).to.eql(200));",
             "const body = pm.response.text();",
             "const pSel = body.match(/name=\"project\"[\\s\\S]*?<\\/select>/);",
             "const pOpt = pSel && pSel[0].match(/<option value=\"(\\d+)\"/);",
             "const dSel = body.match(/name=\"department\"[\\s\\S]*?<\\/select>/);",
             "const dOpt = dSel && dSel[0].match(/<option value=\"(\\d+)\"/);",
             "if (pOpt) pm.collectionVariables.set('projectId', pOpt[1]);",
             "if (dOpt) pm.collectionVariables.set('departmentId', dOpt[1]);",
             "pm.test('Seed project + department available', () => pm.expect(!!pOpt && !!dOpt).to.be.true);",
         ]),
    item("9. Staff creates an NCR (fixture for the horizontal-access checks)", "POST", "/staff-create/",
         headers=[CSRF_HDR], follow=False,
         prereq=[DATE_PREREQ, "pm.collectionVariables.set('secUniq', Date.now());"],
         body=ue([("project", "{{projectId}}"), ("department", "{{departmentId}}"),
                  ("package_no", "SEC-{{secUniq}}"), ("cause", "workmanship"),
                  ("subject", "Security fixture NCR {{secUniq}}"),
                  ("issued_date", "{{issuedDate}}"), ("required_date", "{{requiredDate}}"),
                  ("description", "created by the security collection")]),
         tests=[
             "pm.test('NCR created (302)', () => pm.expect(pm.response.code).to.eql(302));",
             "const m = (pm.response.headers.get('Location') || '').match(/staff-records\\/(\\d+)\\//);",
             "pm.test('New NCR id captured', () => pm.expect(!!m).to.be.true);",
             "if (m) pm.collectionVariables.set('ncrId', m[1]);",
         ]),
    item("10. Staff can open that NCR (staff share record visibility by design)", "GET",
         "/staff-records/{{ncrId}}/",
         tests=["pm.test('Detail page 200', () => pm.expect(pm.response.code).to.eql(200));"],
         desc="Documents the intended model: QA/QC staff see all NCRs, not only their own."),
    logout_step("11. POST /logout/ (switch to admin)"),
    login_step("12. POST login as ADMIN", "{{adminEmail}}", "{{adminPassword}}", ADMIN_DASH, "admin"),
    item("13. Admin cannot read a staff NCR detail page", "GET", "/staff-records/{{ncrId}}/", follow=False,
         tests=[
             "pm.test('Not served to admin (302)', () => pm.expect(pm.response.code).to.eql(302));",
             "pm.test('Sent to the admin dashboard', () =>",
             "  pm.expect(pm.response.headers.get('Location') || '').to.match(%s));" % ADMIN_DASH,
         ]),
    item("14. Admin cannot use the staff export endpoint", "GET", "/staff/export/", follow=False,
         tests=["pm.test('Not served to admin (302)', () => pm.expect(pm.response.code).to.eql(302));"]),
    item("15. Admin cannot open the staff NCR create form", "GET", "/staff-create/", follow=False,
         tests=["pm.test('Not served to admin (302)', () => pm.expect(pm.response.code).to.eql(302));"]),
]

# ---------------------------------------------------------------- 5. injection
sec_injection = [
    logout_step("1. POST /logout/ (anonymous)"),
    login_step("2. POST login as STAFF", "{{staffEmail}}", "{{staffPassword}}", STAFF_DASH, "staff"),
    item("3. SQL injection in the search box is not executed", "GET", "/staff-records/?q={{sqliPayload}}",
         tests=[
             "pm.test('Query handled (200, no 500)', () => pm.expect(pm.response.code).to.eql(200));",
             "pm.test('No database error leaked', () => {",
             "  const b = pm.response.text();",
             "  pm.expect(b).to.not.include('OperationalError');",
             "  pm.expect(b).to.not.include('Traceback');",
             "  pm.expect(b).to.not.include('sqlite3');",
             "});",
         ]),
    item("4. Stacked SQL injection is not executed", "GET",
         "/staff-records/?q=%27%3B%20DROP%20TABLE%20ncr_records%3B--",
         tests=[
             "pm.test('Query handled (200)', () => pm.expect(pm.response.code).to.eql(200));",
             "pm.test('Records table still readable', () => pm.expect(pm.response.text()).to.include('NCR'));",
         ]),
    item("5. Injection attempts in filter parameters are ignored", "GET",
         "/staff-records/?status=%27%20OR%201%3D1--&cause=%27%20OR%201%3D1--&project=1%20OR%201%3D1",
         tests=[
             "pm.test('Invalid filter values ignored (200)', () =>",
             "  pm.expect(pm.response.code).to.eql(200));",
             "pm.test('No database error leaked', () =>",
             "  pm.expect(pm.response.text()).to.not.include('OperationalError'));",
         ]),
    item("6. Malformed date filters do not crash the view", "GET",
         "/staff-records/?date_from=not-a-date&date_to=9999-99-99",
         tests=["pm.test('Handled gracefully (200)', () => pm.expect(pm.response.code).to.eql(200));"]),
    item("7. Reflected XSS in the search term is escaped", "GET",
         "/staff-records/?q=%3Cscript%3Ealert(1)%3C%2Fscript%3E",
         tests=[
             "pm.test('Search handled (200)', () => pm.expect(pm.response.code).to.eql(200));",
             "pm.test('Payload is HTML-escaped (no executable script tag)', () => {",
             "  const b = pm.response.text();",
             "  pm.expect(b).to.not.include('<script>alert');",
             "});",
         ]),
    item("8. Create an NCR whose subject carries a script payload", "POST", "/staff-create/",
         headers=[CSRF_HDR], follow=False,
         prereq=[DATE_PREREQ, "pm.collectionVariables.set('xssUniq', Date.now());"],
         body=ue([("project", "{{projectId}}"), ("department", "{{departmentId}}"),
                  ("package_no", "XSS-{{xssUniq}}"), ("cause", "workmanship"),
                  ("subject", "XSS {{xssPayload}} {{xssUniq}}"),
                  ("issued_date", "{{issuedDate}}"), ("required_date", "{{requiredDate}}"),
                  ("description", "{{xssPayload}}")]),
         tests=[
             "pm.test('Created (302) - the payload is stored, not executed', () =>",
             "  pm.expect(pm.response.code).to.eql(302));",
             "const m = (pm.response.headers.get('Location') || '').match(/staff-records\\/(\\d+)\\//);",
             "pm.test('XSS fixture id captured', () => pm.expect(!!m).to.be.true);",
             "if (m) pm.collectionVariables.set('xssId', m[1]);",
         ]),
    item("9. Stored XSS is escaped on the NCR detail page", "GET", "/staff-records/{{xssId}}/",
         tests=[
             "pm.test('Detail page 200', () => pm.expect(pm.response.code).to.eql(200));",
             "pm.test('Payload never appears as a live <script>', () =>",
             "  pm.expect(pm.response.text()).to.not.include('<script>alert'));",
             "pm.test('Payload is present in escaped form (it really was stored)', () =>",
             "  pm.expect(pm.response.text()).to.include('&lt;script&gt;'));",
         ],
         desc="Both halves matter: absence alone could just mean the payload was dropped."),
    item("10. Stored XSS is escaped in the records list", "GET", "/staff-records/?q=XSS",
         tests=[
             "pm.test('List page 200', () => pm.expect(pm.response.code).to.eql(200));",
             "pm.test('No live script tag in the list', () =>",
             "  pm.expect(pm.response.text()).to.not.include('<script>alert'));",
         ]),
]

# ---------------------------------------------------------------- 6. method tampering
sec_methods = [
    logout_step("1. POST /logout/ (anonymous)"),
    login_step("2. POST login as ADMIN", "{{adminEmail}}", "{{adminPassword}}", ADMIN_DASH, "admin"),
    item("3. PUT on the project edit endpoint is rejected", "PUT", "/admin-projects/{{projectId}}/edit/",
         headers=[CSRF_HDR], follow=False,
         tests=["pm.test('Method Not Allowed (405)', () => pm.expect(pm.response.code).to.eql(405));"]),
    item("4. PATCH on the project edit endpoint is rejected", "PATCH", "/admin-projects/{{projectId}}/edit/",
         headers=[CSRF_HDR], follow=False,
         tests=["pm.test('Method Not Allowed (405)', () => pm.expect(pm.response.code).to.eql(405));"]),
    item("5. DELETE on the project delete endpoint is rejected", "DELETE",
         "/admin-projects/{{projectId}}/delete/", headers=[CSRF_HDR], follow=False,
         tests=[
             "pm.test('Method Not Allowed (405)', () => pm.expect(pm.response.code).to.eql(405));",
             "pm.test('Not deleted (no 302 redirect)', () => pm.expect(pm.response.code).to.not.eql(302));",
         ]),
    logout_step("6. POST /logout/ (switch to staff)"),
    login_step("7. POST login as STAFF", "{{staffEmail}}", "{{staffPassword}}", STAFF_DASH, "staff"),
    item("8. DELETE on the NCR detail endpoint cannot delete a record", "DELETE",
         "/staff-records/{{ncrId}}/", headers=[CSRF_HDR], follow=False,
         tests=[
             "// ncr_detail only acts on POST; other verbs are rendered, never applied",
             "pm.test('No destructive verb accepted (200 render or 405)', () =>",
             "  pm.expect([200, 405]).to.include(pm.response.code));",
         ],
         desc="Current behaviour returns 200 (form re-render) instead of 405 - see the hardening notes."),
    item("9. The NCR is still Open after the DELETE attempt", "GET", "/staff-records/{{ncrId}}/",
         tests=[
             "pm.test('Record still exists (200)', () => pm.expect(pm.response.code).to.eql(200));",
             "pm.test('Status unchanged (still Open)', () =>",
             "  pm.expect(pm.response.text()).to.match(/badge badge-open\">\\s*Open/));",
         ],
         desc="State-integrity check: proves the DELETE above changed nothing."),
]

collection["item"] = [
    {"name": "1. Transport & browser-security headers", "item": sec_headers},
    {"name": "2. Authentication & session integrity", "item": sec_auth},
    {"name": "3. CSRF enforcement", "item": sec_csrf},
    {"name": "4. Authorization (vertical + horizontal)", "item": sec_authz},
    {"name": "5. Injection & input validation", "item": sec_injection},
    {"name": "6. Method tampering & state safety", "item": sec_methods},
]

OUT = os.path.dirname(os.path.abspath(__file__))
path = os.path.join(OUT, "ARKCafe-Security.postman_collection.json")
with open(path, "w", encoding="utf-8") as fh:
    json.dump(collection, fh, ensure_ascii=False, separators=(",", ":"))
print("written:", path)
