# -*- coding: utf-8 -*-
"""Temporary generator: E2E-only Postman collection (v2 - raw URL strings, trailing slashes preserved)."""
import json, sys

CSRF_HDR = {"key": "X-CSRFToken", "value": "{{csrfToken}}"}

def ue(pairs):
    return {"mode": "urlencoded", "urlencoded": [
        {"key": k, "value": v, "type": "text"} for k, v in pairs
    ]}

GUARD_HEADER = "// Skip cleanly if an earlier step failed to capture an ID (avoids a 404 cascade)"
ID_VARS = ("projectId", "departmentId", "ncrId", "ncrRef")

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


def guard_for(path):
    """Pre-request guard for any request whose URL needs a captured ID."""
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
    # Plain string URL: Postman sends it verbatim, trailing slash included.
    req["url"] = "{{baseUrl}}" + path
    it["request"] = req
    return it

collection = {
    "info": {
        "_postman_id": "c4e2d5b6-2222-4a7b-9c8d-2b3c4d5e6f7a",
        "name": "ARKCafe NCR - End-to-End Tests",
        "description": (
            "End-to-end testing through Postman for the ARKCafe / Crimson NCR Django project.\n\n"
            "Two complete user journeys, run top to bottom, with an assertion at every step:\n"
            "  Journey A - Admin : login -> dashboards -> create project & department -> verify -> audit -> cleanup -> logout\n"
            "  Journey B - Staff : login -> dashboard -> raise NCR -> progress -> resolve -> audit -> export -> logout\n\n"
            "Prereqs:\n"
            "  - Django dev server running on {{baseUrl}} (default http://127.0.0.1:8000)\n"
            "  - Environment 'ARKCafe - Local Dev' selected with real admin/staff credentials\n"
            "  - At least one Project and one Department already in the DB (Journey B picks IDs from the records page)\n\n"
            "Django sessions + CSRF are handled automatically: the collection-level script keeps\n"
            "{{csrfToken}} synced with the csrftoken cookie; every POST sends X-CSRFToken.\n\n"
            "NOTE: all URLs include Django's required trailing slash. Do not remove it -\n"
            "Django cannot redirect a POST to the slashed URL without losing the POST data."
        ),
        "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
    },
    "item": [],
    "variable": [
        {"key": "csrfToken", "value": "", "type": "string"},
        {"key": "projectId", "value": "", "type": "string"},
        {"key": "departmentId", "value": "", "type": "string"},
        {"key": "ncrId", "value": "", "type": "string"},
        {"key": "projectCode", "value": "", "type": "string"},
        {"key": "projectName", "value": "", "type": "string"},
        {"key": "departmentName", "value": "", "type": "string"},
        {"key": "uniq", "value": "", "type": "string"},
    ],
    "event": [{
        "listen": "test",
        "script": {"type": "text/javascript", "exec": [
            "// Keep the Django CSRF token in sync with the csrftoken cookie",
            "try {",
            "  const ck = pm.cookies.get('csrftoken');",
            "  if (ck) pm.collectionVariables.set('csrfToken', ck);",
            "} catch (e) { /* cookie jar not available in this context */ }",
        ]},
    }],
}

environment = {
    "name": "ARKCafe - Local Dev",
    "values": [
        {"key": "baseUrl", "value": "http://127.0.0.1:8000", "enabled": True},
        {"key": "adminEmail", "value": "admin@test.com", "enabled": True},
        {"key": "adminPassword", "value": "Passw0rd!123", "enabled": True, "type": "secret"},
        {"key": "staffEmail", "value": "staff@test.com", "enabled": True},
        {"key": "staffPassword", "value": "Passw0rd!123", "enabled": True, "type": "secret"},
    ],
    "_postman_variable_scope": "environment",
}

# ---------------------------------------------------------------- Journey A - Admin
e2e_admin = [
    item("0a. Open /login/ (acquire a CSRF cookie)", "GET", "/login/",
         prereq=[
             "// Clear per-run variables so a previous failed run cannot leak IDs",
             "['projectId','departmentId','ncrId','projectCode','projectName','departmentName','ncrRef','uniq']",
             "  .forEach(function(k){ pm.collectionVariables.unset(k); });",
         ],
         tests=[
             "// A live session from a previous run returns 302 to that role's dashboard - that is fine here",
             "pm.test('Login route reachable', () => pm.expect([200, 302]).to.include(pm.response.code));",
         ],
         desc="Guarantees the csrftoken cookie exists so the next POST /logout/ is not rejected."),
    item("0b. Ensure signed out (POST /logout/)", "POST", "/logout/", headers=[CSRF_HDR], follow=False,
         tests=[
             "pm.test('Sign-out attempted', () => pm.expect([200, 302, 403]).to.include(pm.response.code));",
         ],
         desc="Clears any session left by an earlier failed run so step 1 really tests the anonymous case."),
    item("1. Open / (anonymous) - lands on login page", "GET", "/",
         tests=[
             "pm.test('Lands on login page (200)', () => pm.expect(pm.response.code).to.eql(200));",
             "pm.test('Email field present', () => pm.expect(pm.response.text()).to.include('name=\"username\"'));",
         ],
         desc="Follows the redirect chain / -> /login/ like a real browser."),
    item("2. Login as ADMIN", "POST", "/login/", headers=[CSRF_HDR], follow=False,
         body=ue([("username", "{{adminEmail}}"), ("password", "{{adminPassword}}")]),
         tests=[
             "pm.test('Redirected (302)', () => pm.expect(pm.response.code).to.eql(302));",
             "pm.test('Sent to an admin dashboard', () =>",
             "  pm.expect(pm.response.headers.get('Location') || '').to.match(/admin-dashboard|reports\\/admin\\/dashboard/));",
             "pm.test('sessionid cookie issued', () => pm.expect(!!pm.cookies.get('sessionid')).to.be.true);",
         ]),
    item("3. Admin dashboard visible", "GET", "/admin-dashboard/",
         tests=[
             "pm.test('Dashboard 200', () => pm.expect(pm.response.code).to.eql(200));",
             "pm.test('App shell rendered', () => pm.expect(pm.response.text()).to.include('Crimson NCR'));",
             "pm.test('Admin-only shell rendered (admin sidebar link)', () =>",
             "  pm.expect(pm.response.text()).to.include('/admin-users/'));",
         ]),
    item("4. Reports admin dashboard visible", "GET", "/reports/admin/dashboard/",
         tests=["pm.test('Reports dashboard 200', () => pm.expect(pm.response.code).to.eql(200));"]),
    item("5. Create a new project", "POST", "/admin-projects/add/", headers=[CSRF_HDR], follow=False,
         prereq=[
             "pm.collectionVariables.set('projectCode', 'E2E-' + Date.now());",
             "pm.collectionVariables.set('projectName', 'E2E Project ' + Date.now());",
         ],
         body=ue([("project_name", "{{projectName}}"), ("client_name", "E2E Client"),
                  ("project_code", "{{projectCode}}"), ("description", "E2E admin journey")]),
         tests=[
             "pm.test('Project created (302)', () => pm.expect(pm.response.code).to.eql(302));",
             "pm.test('Sent back to projects list', () =>",
             "  pm.expect(pm.response.headers.get('Location') || '').to.include('admin-projects'));",
         ]),
    item("6. Create a new department", "POST", "/admin-departments/", headers=[CSRF_HDR], follow=False,
         prereq=["pm.collectionVariables.set('departmentName', 'E2E Dept ' + Date.now());"],
         body=ue([("action", "add"), ("add-department_name", "{{departmentName}}")]),
         tests=[
             "pm.test('Department created (302)', () => pm.expect(pm.response.code).to.eql(302));",
             "pm.test('Sent back to departments list', () =>",
             "  pm.expect(pm.response.headers.get('Location') || '').to.include('admin-departments'));",
         ]),
    item("7. Verify project appears in admin list", "GET", "/admin-projects/?q={{projectCode}}",
         tests=[
             "pm.test('Project visible in list', () => pm.expect(pm.response.text()).to.include(pm.collectionVariables.get('projectCode')));",
             "var escCode = pm.collectionVariables.get('projectCode').replace(/[.*+?^${}()|[\\]\\\\]/g, '\\\\$&');",
             "const m = pm.response.text().match(new RegExp('admin-projects/(\\\\d+)/edit/[\\\\s\\\\S]{0,300}?data-project_code=\"' + escCode + '\"'));",
             "pm.test('Project row found (matched by code)', () => pm.expect(!!m).to.be.true);",
             "if (m) pm.collectionVariables.set('projectId', m[1]);",
         ]),
    item("8. Verify department appears in admin list", "GET", "/admin-departments/?q={{departmentName}}",
         tests=[
             "pm.test('Department visible in list', () => pm.expect(pm.response.text()).to.include(pm.collectionVariables.get('departmentName')));",
             "var escaped = pm.collectionVariables.get('departmentName').replace(/[.*+?^${}()|[\\]\\\\]/g, '\\\\$&');",
             "const m = pm.response.text().match(new RegExp('data-id=\"(\\\\d+)\"[\\\\s\\\\S]{0,200}?data-name=\"' + escaped + '\"'));",
             "pm.test('Department row found (matched by name)', () => pm.expect(!!m).to.be.true);",
             "if (m) pm.collectionVariables.set('departmentId', m[1]);",
         ]),
    item("9. Audit history accessible", "GET", "/admin-audit/",
         tests=["pm.test('Admin audit page 200', () => pm.expect(pm.response.code).to.eql(200));"]),
    item("10. Cleanup: delete created project", "POST", "/admin-projects/{{projectId}}/delete/",
         headers=[CSRF_HDR], follow=False,
         tests=[
             "pm.test('Project deleted (302)', () => pm.expect(pm.response.code).to.eql(302));",
             "pm.test('Sent back to projects list', () =>",
             "  pm.expect(pm.response.headers.get('Location') || '').to.include('admin-projects'));",
         ]),
    item("11. Verify project no longer listed", "GET", "/admin-projects/?q={{projectCode}}",
         tests=[
             "pm.test('Project gone after deletion', () =>",
             "  pm.expect(pm.response.text()).to.not.include('data-project_code=\"' + pm.collectionVariables.get('projectCode') + '\"'));",
         ]),
    item("12. Cleanup: delete created department", "POST", "/admin-departments/",
         headers=[CSRF_HDR], follow=False,
         body=ue([("action", "delete"), ("department_id", "{{departmentId}}")]),
         tests=[
             "pm.test('Department deleted (302)', () => pm.expect(pm.response.code).to.eql(302));",
             "pm.test('Sent back to departments list', () =>",
             "  pm.expect(pm.response.headers.get('Location') || '').to.include('admin-departments'));",
         ]),
    item("13. Verify department no longer listed", "GET", "/admin-departments/?q={{departmentName}}",
         tests=[
             "pm.test('Department gone after deletion', () =>",
             "  pm.expect(pm.response.text()).to.not.include('data-name=\"' + pm.collectionVariables.get('departmentName') + '\"'));",
         ]),
    item("14. Logout - journey ends", "POST", "/logout/", headers=[CSRF_HDR], follow=False,
         tests=[
             "pm.test('Logged out (302)', () => pm.expect([200, 302]).to.include(pm.response.code));",
             "pm.test('Session cleared', () => pm.expect(pm.cookies.get('sessionid') || '').to.eql(''));",
         ]),
]

# ---------------------------------------------------------------- Journey B - Staff
e2e_staff = [
    item("0a. Open /login/ (acquire a CSRF cookie)", "GET", "/login/",
         prereq=[
             "// Clear per-run variables so a previous failed run cannot leak state into this one",
             "['projectId','departmentId','ncrId','ncrRef','uniq'].forEach(function(k){ pm.collectionVariables.unset(k); });",
         ],
         tests=[
             "// A live session from a previous run returns 302 to that role's dashboard - that is fine here",
             "pm.test('Login route reachable', () => pm.expect([200, 302]).to.include(pm.response.code));",
         ]),
    item("0b. Ensure signed out (POST /logout/)", "POST", "/logout/", headers=[CSRF_HDR], follow=False,
         tests=[
             "pm.test('Sign-out attempted', () => pm.expect([200, 302, 403]).to.include(pm.response.code));",
         ],
         desc="Clears any session left by an earlier failed run so step 1 really tests the anonymous case."),
    item("1. Open login page (fresh CSRF)", "GET", "/login/",
         tests=["pm.test('Login page 200', () => pm.expect(pm.response.code).to.eql(200));"]),
    item("2. Login as STAFF", "POST", "/login/", headers=[CSRF_HDR], follow=False,
         body=ue([("username", "{{staffEmail}}"), ("password", "{{staffPassword}}")]),
         tests=[
             "pm.test('Redirected (302)', () => pm.expect(pm.response.code).to.eql(302));",
             "pm.test('Sent to the staff dashboard', () =>",
             "  pm.expect(pm.response.headers.get('Location') || '').to.match(/staff-dashboard|staff\\/dashboard/));",
             "pm.test('sessionid cookie issued', () => pm.expect(!!pm.cookies.get('sessionid')).to.be.true);",
         ]),
    item("3. Staff dashboard visible", "GET", "/staff-dashboard/",
         tests=[
             "pm.test('Dashboard 200', () => pm.expect(pm.response.code).to.eql(200));",
             "pm.test('Staff-only shell rendered (staff sidebar link)', () =>",
             "  pm.expect(pm.response.text()).to.include('/staff-create/'));",
         ]),
    item("4. Open create form - capture project & department IDs", "GET", "/staff-create/",
         tests=[
             "pm.test('Create form 200', () => pm.expect(pm.response.code).to.eql(200));",
             "const body = pm.response.text();",
             "const pSel = body.match(/name=\"project\"[\\s\\S]*?<\\/select>/);",
             "const pOpt = pSel && pSel[0].match(/<option value=\"(\\d+)\"/);",
             "const dSel = body.match(/name=\"department\"[\\s\\S]*?<\\/select>/);",
             "const dOpt = dSel && dSel[0].match(/<option value=\"(\\d+)\"/);",
             "if (pOpt) pm.collectionVariables.set('projectId', pOpt[1]);",
             "if (dOpt) pm.collectionVariables.set('departmentId', dOpt[1]);",
             "pm.test('Seed data available (project + department)', () => pm.expect(!!pOpt && !!dOpt).to.be.true);",
         ],
         desc="Needs at least one project and one department in the DB."),
    item("5. Raise a new NCR", "POST", "/staff-create/", headers=[CSRF_HDR], follow=False,
         prereq=[DATE_PREREQ, "pm.collectionVariables.set('uniq', Date.now());"],
         body=ue([("project", "{{projectId}}"), ("department", "{{departmentId}}"),
                  ("package_no", "PKG-{{uniq}}"), ("cause", "workmanship"),
                  ("subject", "E2E staff journey NCR {{uniq}}"),
                  ("issued_date", "{{issuedDate}}"), ("required_date", "{{requiredDate}}"),
                  ("description", "Raised end-to-end by the staff journey")]),
         tests=[
             "pm.test('NCR created (302)', () => pm.expect(pm.response.code).to.eql(302));",
             "const m = (pm.response.headers.get('Location') || '').match(/staff-records\\/(\\d+)\\//);",
             "pm.test('Sent to new NCR detail', () => pm.expect(!!m).to.be.true);",
             "if (m) pm.collectionVariables.set('ncrId', m[1]);",
         ]),
    item("6. Open NCR detail - verify created as Open", "GET", "/staff-records/{{ncrId}}/",
         tests=[
             "pm.test('Detail 200', () => pm.expect(pm.response.code).to.eql(200));",
             "pm.test('Reference auto-generated (NCR-...)', () => pm.expect(pm.response.text()).to.match(/NCR-\\d{4}-\\d{4}/));",
             "const refM = pm.response.text().match(/NCR-\\d{4}-\\d{4}/);",
             "if (refM) pm.collectionVariables.set('ncrRef', refM[0]);",
             "// Check the status badge next to THIS NCR's reference, not a substring anywhere on the page",
             "// The flash message repeats the reference before the card; match the title-bar markup instead",
             "pm.test('Status badge is Open', () =>",
             "  pm.expect(pm.response.text()).to.match(/NCR-\\d{4}-\\d{4}<\\/h2>\\s*<span class=\"badge badge-open\">[\\s\\S]{0,120}?\\bOpen\\b/));",
         ]),
    item("7. Start work: open -> in_progress", "POST", "/staff-records/{{ncrId}}/",
         headers=[CSRF_HDR], follow=False,
         body=ue([("new_status", "in_progress"), ("remarks", "E2E journey")]),
         tests=[
             "pm.test('Moved to In Progress (302)', () => pm.expect(pm.response.code).to.eql(302));",
             "pm.test('Sent back to the same NCR detail', () =>",
             "  pm.expect(pm.response.headers.get('Location') || '').to.include('/staff-records/' + pm.collectionVariables.get('ncrId') + '/'));",
         ]),
    item("8. Verify status In Progress", "GET", "/staff-records/{{ncrId}}/",
         tests=[
             "pm.test('Status badge is In Progress', () =>",
             "  pm.expect(pm.response.text()).to.match(/NCR-\\d{4}-\\d{4}<\\/h2>\\s*<span class=\"badge badge-in_progress\">[\\s\\S]{0,120}?\\bIn Progress\\b/));",
         ]),
    item("9. Resolve the NCR (with resolution type)", "POST", "/staff-records/{{ncrId}}/",
         headers=[CSRF_HDR], follow=False,
         body=ue([("new_status", "resolved"), ("resolution_type", "reapproved"),
                  ("resolution_note", "Approved after rework"), ("remarks", "E2E journey")]),
         tests=[
             "pm.test('Resolved (302)', () => pm.expect(pm.response.code).to.eql(302));",
             "pm.test('Sent back to the same NCR detail', () =>",
             "  pm.expect(pm.response.headers.get('Location') || '').to.include('/staff-records/' + pm.collectionVariables.get('ncrId') + '/'));",
         ]),
    item("10. Verify Resolved + resolution history logged", "GET", "/staff-records/{{ncrId}}/",
         tests=[
             "pm.test('Status badge is Resolved', () =>",
             "  pm.expect(pm.response.text()).to.match(/NCR-\\d{4}-\\d{4}<\\/h2>\\s*<span class=\"badge badge-resolved\">[\\s\\S]{0,120}?\\bResolved\\b/));",
             "pm.test('History shows journey remarks', () => pm.expect(pm.response.text()).to.match(/E2E journey/));",
         ]),
    item("11. Audit history contains this NCR's reference", "GET", "/staff/audit-history/?q={{ncrRef}}",
         tests=[
             "pm.test('Audit history 200', () => pm.expect(pm.response.code).to.eql(200));",
             "pm.test('Audit row exists for this NCR', () =>",
             "  pm.expect(pm.response.text()).to.include(pm.collectionVariables.get('ncrRef')));",
         ]),
    item("12. Export the NCR list (Excel)", "POST", "/staff/export/", headers=[CSRF_HDR],
         body={"mode": "formdata", "formdata": [
             {"key": "export_type", "value": "excel", "type": "text"},
             {"key": "columns", "value": "reference_no", "type": "text"},
             {"key": "columns", "value": "subject", "type": "text"},
             {"key": "columns", "value": "status", "type": "text"}]},
         tests=[
             "pm.test('Export 200', () => pm.expect(pm.response.code).to.eql(200));",
             "pm.test('xlsx content type', () => pm.expect(pm.response.headers.get('Content-Type') || '').to.include('spreadsheetml'));",
             "pm.test('Sent as attachment', () =>",
             "  pm.expect(pm.response.headers.get('Content-Disposition') || '').to.include('attachment'));",
             "pm.test('Body is a non-empty xlsx (PK zip signature)', () => {",
             "  pm.expect(pm.response.text().slice(0, 2)).to.eql('PK');",
             "  pm.expect(Number(pm.response.headers.get('X-Export-Records'))).to.be.at.least(1);",
             "  pm.expect(pm.response.headers.get('X-Export-Filename') || '').to.match(/\\.xlsx$/);",
             "});",
         ]),
    item("13. Logout - journey ends", "POST", "/logout/", headers=[CSRF_HDR], follow=False,
         tests=[
             "pm.test('Logged out (302)', () => pm.expect([200, 302]).to.include(pm.response.code));",
             "pm.test('Session cleared', () => pm.expect(pm.cookies.get('sessionid') || '').to.eql(''));",
         ]),
]

collection["item"] = [
    {"name": "Journey A - Admin", "item": e2e_admin},
    {"name": "Journey B - Staff (QA/QC)", "item": e2e_staff},
]

sep = "\n=====ENV=====\n"
sys.stdout.write(json.dumps(collection, ensure_ascii=False, separators=(",", ":")) + sep +
                 json.dumps(environment, ensure_ascii=False, separators=(",", ":")))
