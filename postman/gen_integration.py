# -*- coding: utf-8 -*-
"""Temporary generator: creates ARKCafe-Integration.postman_collection.json (URLs as raw strings).
Run from anywhere:  python postman/gen_integration.py   — then delete this file."""
import json, os

OUT = os.path.dirname(os.path.abspath(__file__))
CSRF_HDR = {"key": "X-CSRFToken", "value": "{{csrfToken}}"}

def ue(pairs):
    return {"mode": "urlencoded", "urlencoded": [
        {"key": k, "value": v, "type": "text"} for k, v in pairs
    ]}

def fd(pairs):
    return {"mode": "formdata", "formdata": [
        {"key": k, "value": v, "type": "text"} for k, v in pairs
    ]}

GUARD_HEADER = "// Skip cleanly if an earlier step failed to capture an ID (avoids a 404 cascade)"
ID_VARS = ("projectId", "departmentId", "ncrId", "ncrRef")


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
    req["url"] = "{{baseUrl}}" + path  # raw string keeps Django's trailing slash
    it["request"] = req
    return it

collection = {
    "info": {
        "_postman_id": "d5f3e6c7-3333-4a7b-9c8d-3c4d5e6f7a8b",
        "name": "ARKCafe NCR - Integration Tests",
        "description": (
            "Integration testing for the ARKCafe / Crimson NCR Django project: chained multi-request\n"
            "flows that share session/CSRF state and pass IDs between requests via collection variables.\n\n"
            "Folders run in order:\n"
            "  1. Admin session & dashboards\n"
            "  2. Projects CRUD chain (creates its own project, unique code per run)\n"
            "  3. Departments CRUD chain (creates its own department, unique name per run)\n"
            "  4. Logout & session invalidation\n"
            "  5. Staff NCR lifecycle (create -> status transitions -> edit -> search -> export)\n\n"
            "Prereqs: dev server on {{baseUrl}}, environment 'ARKCafe - Local Dev' selected,\n"
            "at least one Project and one Department in the DB (staff NCR chain picks IDs from the records page).\n"
            "Uses the SAME environment as the E2E collection. All URLs keep Django's trailing slash."
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

# ---------------------------------------------------------------- 1. Admin session
int_admin = [
    item("0a. GET /login/ (acquire a CSRF cookie)", "GET", "/login/",
         prereq=[
             "// Clear per-run variables so a previous failed run cannot leak state into this one",
             "['projectId','departmentId','ncrId','ncrRef','projectCode','projectName','departmentName','uniq']",
             "  .forEach(function(k){ pm.collectionVariables.unset(k); });",
         ],
         tests=[
             "// A live session from a previous run returns 302 to that role's dashboard - that is fine here",
             "pm.test('Login route reachable', () => pm.expect([200, 302]).to.include(pm.response.code));",
         ]),
    item("0b. POST /logout/ (ensure signed out)", "POST", "/logout/", headers=[CSRF_HDR], follow=False,
         tests=["pm.test('Sign-out attempted', () => pm.expect([200, 302, 403]).to.include(pm.response.code));"]),
    item("1. GET login page (fresh CSRF)", "GET", "/login/",
         tests=["pm.test('Login page 200', () => pm.expect(pm.response.code).to.eql(200));"]),
    item("2. POST login as ADMIN", "POST", "/login/", headers=[CSRF_HDR], follow=False,
         body=ue([("username", "{{adminEmail}}"), ("password", "{{adminPassword}}")]),
         tests=[
             "pm.test('Login redirects (302)', () => pm.expect(pm.response.code).to.eql(302));",
             "pm.test('Sent to an admin dashboard', () =>",
             "  pm.expect(pm.response.headers.get('Location') || '').to.match(/admin-dashboard|reports\\/admin\\/dashboard/));",
             "pm.test('sessionid cookie issued', () => pm.expect(!!pm.cookies.get('sessionid')).to.be.true);",
         ]),
    item("3. GET admin dashboard renders (session works)", "GET", "/admin-dashboard/",
         tests=[
             "pm.test('Dashboard 200', () => pm.expect(pm.response.code).to.eql(200));",
             "pm.test('Authenticated shell rendered', () => pm.expect(pm.response.text()).to.include('Crimson NCR'));",
             "pm.test('Admin-only shell rendered (admin sidebar link)', () =>",
             "  pm.expect(pm.response.text()).to.include('/admin-users/'));",
         ]),
    item("4. GET reports admin dashboard renders", "GET", "/reports/admin/dashboard/",
         tests=["pm.test('Reports dashboard 200', () => pm.expect(pm.response.code).to.eql(200));"]),
]

# ---------------------------------------------------------------- 2. Projects CRUD
int_projects = [
    item("1. POST add project (unique code per run)", "POST", "/admin-projects/add/",
         headers=[CSRF_HDR], follow=False,
         prereq=[
             "pm.collectionVariables.set('projectCode', 'INT-' + Date.now());",
             "pm.collectionVariables.set('projectName', 'Integration Project');",
         ],
         body=ue([("project_name", "{{projectName}}"), ("client_name", "Integration Client"),
                  ("project_code", "{{projectCode}}"), ("description", "Created by integration test")]),
         tests=[
             "pm.test('Add project redirects (302)', () => pm.expect(pm.response.code).to.eql(302));",
         ]),
    item("2. GET list - new project visible, capture ID", "GET", "/admin-projects/?q={{projectCode}}",
         tests=[
             "pm.test('Project list 200', () => pm.expect(pm.response.code).to.eql(200));",
             "pm.test('New project appears in list', () => pm.expect(pm.response.text()).to.include(pm.collectionVariables.get('projectCode')));",
             "var escCode = pm.collectionVariables.get('projectCode').replace(/[.*+?^${}()|[\\]\\\\]/g, '\\\\$&');",
             "const m = pm.response.text().match(new RegExp('admin-projects/(\\\\d+)/edit/[\\\\s\\\\S]{0,300}?data-project_code=\"' + escCode + '\"'));",
             "pm.test('Project row found (matched by code)', () => pm.expect(!!m).to.be.true);",
             "if (m) pm.collectionVariables.set('projectId', m[1]);",
         ]),
    item("3. POST edit project", "POST", "/admin-projects/{{projectId}}/edit/",
         headers=[CSRF_HDR], follow=False,
         body=ue([("project_name", "{{projectName}} - EDITED"), ("client_name", "Integration Client"),
                  ("project_code", "{{projectCode}}"), ("description", "Edited by integration test")]),
         tests=[
             "pm.test('Edit redirects (302)', () => pm.expect(pm.response.code).to.eql(302));",
             "pm.test('Sent back to projects list', () =>",
             "  pm.expect(pm.response.headers.get('Location') || '').to.include('admin-projects'));",
         ]),
    item("4. GET list - edit persisted", "GET", "/admin-projects/?q={{projectCode}}",
         tests=[
             "pm.test('Edited name is visible', () => pm.expect(pm.response.text()).to.include(pm.collectionVariables.get('projectName') + ' - EDITED'));",
         ]),
    item("5. POST delete project", "POST", "/admin-projects/{{projectId}}/delete/",
         headers=[CSRF_HDR], follow=False,
         tests=[
             "pm.test('Delete redirects (302)', () => pm.expect(pm.response.code).to.eql(302));",
             "pm.test('Sent back to projects list', () =>",
             "  pm.expect(pm.response.headers.get('Location') || '').to.include('admin-projects'));",
         ]),
    item("6. GET list - deletion persisted", "GET", "/admin-projects/?q={{projectCode}}",
         tests=[
             "pm.test('Project no longer listed', () =>",
             "  pm.expect(pm.response.text()).to.not.include('admin-projects/' + pm.collectionVariables.get('projectId') + '/edit/'));",
         ]),
]

# ---------------------------------------------------------------- 3. Departments CRUD
int_departments = [
    item("1. POST add department (unique name per run)", "POST", "/admin-departments/",
         headers=[CSRF_HDR], follow=False,
         prereq=["pm.collectionVariables.set('departmentName', 'Int Dept ' + Date.now());"],
         body=ue([("action", "add"), ("add-department_name", "{{departmentName}}")]),
         tests=[
             "pm.test('Add department redirects (302)', () => pm.expect(pm.response.code).to.eql(302));",
             "pm.test('Sent back to departments list', () =>",
             "  pm.expect(pm.response.headers.get('Location') || '').to.include('admin-departments'));",
         ]),
    item("2. GET list - new department visible, capture ID", "GET", "/admin-departments/?q={{departmentName}}",
         tests=[
             "pm.test('Department visible in list', () => pm.expect(pm.response.text()).to.include(pm.collectionVariables.get('departmentName')));",
             "var escName = pm.collectionVariables.get('departmentName').replace(/[.*+?^${}()|[\\]\\\\]/g, '\\\\$&');",
             "const m = pm.response.text().match(new RegExp('data-id=\"(\\\\d+)\"[\\\\s\\\\S]{0,200}?data-name=\"' + escName + '\"'));",
             "pm.test('Department row found (matched by name)', () => pm.expect(!!m).to.be.true);",
             "if (m) pm.collectionVariables.set('departmentId', m[1]);",
         ]),
    item("3. POST rename department", "POST", "/admin-departments/",
         headers=[CSRF_HDR], follow=False,
         prereq=["pm.collectionVariables.set('departmentName', pm.collectionVariables.get('departmentName') + ' RENAMED');"],
         body=ue([("action", "rename"), ("department_id", "{{departmentId}}"),
                  ("rename-department_name", "{{departmentName}}")]),
         tests=[
             "pm.test('Rename redirects (302)', () => pm.expect(pm.response.code).to.eql(302));",
             "pm.test('Sent back to departments list', () =>",
             "  pm.expect(pm.response.headers.get('Location') || '').to.include('admin-departments'));",
         ]),
    item("4. GET list - rename persisted", "GET", "/admin-departments/?q={{departmentName}}",
         tests=[
             "pm.test('Renamed department is visible', () => pm.expect(pm.response.text()).to.include(pm.collectionVariables.get('departmentName')));",
         ]),
    item("5. POST delete department", "POST", "/admin-departments/",
         headers=[CSRF_HDR], follow=False,
         body=ue([("action", "delete"), ("department_id", "{{departmentId}}")]),
         tests=[
             "pm.test('Delete redirects (302)', () => pm.expect(pm.response.code).to.eql(302));",
             "pm.test('Sent back to departments list', () =>",
             "  pm.expect(pm.response.headers.get('Location') || '').to.include('admin-departments'));",
         ]),
    item("6. GET list - deletion persisted", "GET", "/admin-departments/?q={{departmentName}}",
         tests=[
             "pm.test('Department no longer listed', () =>",
             "  pm.expect(pm.response.text()).to.not.include('data-name=\"' + pm.collectionVariables.get('departmentName') + '\"'));",
         ]),
]

# ---------------------------------------------------------------- 4. Logout
int_logout = [
    item("1. POST logout", "POST", "/logout/", headers=[CSRF_HDR], follow=False,
         tests=["pm.test('Logout redirects', () => pm.expect([200, 302]).to.include(pm.response.code));"]),
    item("2. GET admin dashboard after logout is rejected", "GET", "/admin-dashboard/", follow=False,
         tests=[
             "pm.test('Session invalidated: not served (302)', () => pm.expect(pm.response.code).to.eql(302));",
             "pm.test('Redirected to login', () =>",
             "  pm.expect(pm.response.headers.get('Location') || '').to.include('/login/'));",
         ]),
]

# ---------------------------------------------------------------- 5. Staff NCR lifecycle
int_ncr = [
    item("0a. GET /login/ (acquire a CSRF cookie)", "GET", "/login/",
         prereq=[
             "// Clear per-run variables so a previous failed run cannot leak state into this one",
             "['projectId','departmentId','ncrId','ncrRef','uniq'].forEach(function(k){ pm.collectionVariables.unset(k); });",
         ],
         tests=[
             "// A live session from a previous run returns 302 to that role's dashboard - that is fine here",
             "pm.test('Login route reachable', () => pm.expect([200, 302]).to.include(pm.response.code));",
         ]),
    item("0b. POST /logout/ (ensure signed out)", "POST", "/logout/", headers=[CSRF_HDR], follow=False,
         tests=["pm.test('Sign-out attempted', () => pm.expect([200, 302, 403]).to.include(pm.response.code));"]),
    item("1. GET login page (fresh CSRF)", "GET", "/login/",
         tests=["pm.test('Login page 200', () => pm.expect(pm.response.code).to.eql(200));"]),
    item("2. POST login as STAFF", "POST", "/login/", headers=[CSRF_HDR], follow=False,
         body=ue([("username", "{{staffEmail}}"), ("password", "{{staffPassword}}")]),
         tests=[
             "pm.test('Login redirects (302)', () => pm.expect(pm.response.code).to.eql(302));",
             "pm.test('Sent to the staff dashboard', () =>",
             "  pm.expect(pm.response.headers.get('Location') || '').to.match(/staff-dashboard|staff\\/dashboard/));",
             "pm.test('sessionid cookie issued', () => pm.expect(!!pm.cookies.get('sessionid')).to.be.true);",
         ]),
    item("3. GET create form - capture project & department IDs", "GET", "/staff-create/",
         tests=[
             "pm.test('Create form 200', () => pm.expect(pm.response.code).to.eql(200));",
             "const body = pm.response.text();",
             "const pSel = body.match(/name=\"project\"[\\s\\S]*?<\\/select>/);",
             "const pOpt = pSel && pSel[0].match(/<option value=\"(\\d+)\"/);",
             "const dSel = body.match(/name=\"department\"[\\s\\S]*?<\\/select>/);",
             "const dOpt = dSel && dSel[0].match(/<option value=\"(\\d+)\"/);",
             "if (pOpt) pm.collectionVariables.set('projectId', pOpt[1]);",
             "if (dOpt) pm.collectionVariables.set('departmentId', dOpt[1]);",
             "pm.test('Seed data found (project + department)', () => pm.expect(!!pOpt && !!dOpt).to.be.true);",
         ]),
    item("4. POST create NCR - capture new NCR ID from redirect", "POST", "/staff-create/",
         headers=[CSRF_HDR], follow=False,
         prereq=["pm.collectionVariables.set('uniq', Date.now());"],
         body=ue([("project", "{{projectId}}"), ("department", "{{departmentId}}"),
                  ("package_no", "PKG-{{uniq}}"), ("cause", "material"),
                  ("subject", "Integration NCR {{uniq}}"),
                  ("issued_date", "2026-01-15"), ("required_date", "2026-02-15"),
                  ("description", "Created by the integration suite")]),
         tests=[
             "pm.test('Create NCR redirects (302)', () => pm.expect(pm.response.code).to.eql(302));",
             "const m = (pm.response.headers.get('Location') || '').match(/staff-records\\/(\\d+)\\//);",
             "pm.test('Redirects to the new NCR detail', () => pm.expect(!!m).to.be.true);",
             "if (m) pm.collectionVariables.set('ncrId', m[1]);",
         ]),
    item("5. GET detail - created as OPEN with auto reference", "GET", "/staff-records/{{ncrId}}/",
         tests=[
             "pm.test('Detail page 200', () => pm.expect(pm.response.code).to.eql(200));",
             "pm.test('Reference auto-generated (NCR-...)', () => pm.expect(pm.response.text()).to.match(/NCR-\\d{4}-\\d{4}/));",
             "const refM = pm.response.text().match(/NCR-\\d{4}-\\d{4}/);",
             "if (refM) pm.collectionVariables.set('ncrRef', refM[0]);",
             "// Check the status badge next to THIS NCR's reference, not a substring anywhere on the page",
             "// The flash message repeats the reference before the card; match the title-bar markup instead",
             "pm.test('Status badge is Open', () =>",
             "  pm.expect(pm.response.text()).to.match(/NCR-\\d{4}-\\d{4}<\\/span>\\s*<span class=\"badge badge-open\">\\s*Open/));",
         ]),
    item("6. POST resolve without resolution type (invalid, stays open)", "POST", "/staff-records/{{ncrId}}/",
         headers=[CSRF_HDR],
         body=ue([("new_status", "resolved"), ("remarks", "missing resolution type")]),
         tests=[
             "pm.test('Invalid status change re-renders form (200)', () => pm.expect(pm.response.code).to.eql(200));",
             "pm.test('Resolution-type error shown', () => pm.expect(pm.response.text()).to.include('Choose how this NCR was resolved'));",
             "pm.test('Status unchanged: badge still Open', () =>",
             "  pm.expect(pm.response.text()).to.match(/NCR-\\d{4}-\\d{4}<\\/span>\\s*<span class=\"badge badge-open\">\\s*Open/));",
         ]),
    item("7. POST status: open -> in_progress", "POST", "/staff-records/{{ncrId}}/",
         headers=[CSRF_HDR], follow=False,
         body=ue([("new_status", "in_progress"), ("remarks", "WIP by integration test")]),
         tests=[
             "pm.test('Status update redirects (302)', () => pm.expect(pm.response.code).to.eql(302));",
             "pm.test('Sent back to the same NCR detail', () =>",
             "  pm.expect(pm.response.headers.get('Location') || '').to.include('/staff-records/' + pm.collectionVariables.get('ncrId') + '/'));",
         ]),
    item("8. GET detail - In Progress", "GET", "/staff-records/{{ncrId}}/",
         tests=[
             "pm.test('Status badge is In Progress', () =>",
             "  pm.expect(pm.response.text()).to.match(/NCR-\\d{4}-\\d{4}<\\/span>\\s*<span class=\"badge badge-in_progress\">\\s*In Progress/));",
         ]),
    item("9. POST resolve (in_progress -> resolved, with type)", "POST", "/staff-records/{{ncrId}}/",
         headers=[CSRF_HDR], follow=False,
         body=ue([("new_status", "resolved"), ("resolution_type", "closed"),
                  ("resolution_note", "Fixed and re-approved"), ("remarks", "Resolved by integration test")]),
         tests=[
             "pm.test('Resolve redirects (302)', () => pm.expect(pm.response.code).to.eql(302));",
             "pm.test('Sent back to the same NCR detail', () =>",
             "  pm.expect(pm.response.headers.get('Location') || '').to.include('/staff-records/' + pm.collectionVariables.get('ncrId') + '/'));",
         ]),
    item("10. GET detail - Resolved", "GET", "/staff-records/{{ncrId}}/",
         tests=[
             "pm.test('Status badge is Resolved', () =>",
             "  pm.expect(pm.response.text()).to.match(/NCR-\\d{4}-\\d{4}<\\/span>\\s*<span class=\"badge badge-resolved\">\\s*Resolved/));",
         ]),
    item("11. POST reopen (resolved -> open)", "POST", "/staff-records/{{ncrId}}/",
         headers=[CSRF_HDR], follow=False,
         body=ue([("new_status", "open"), ("remarks", "Reopened by integration test")]),
         tests=[
             "pm.test('Reopen redirects (302)', () => pm.expect(pm.response.code).to.eql(302));",
             "pm.test('Sent back to the same NCR detail', () =>",
             "  pm.expect(pm.response.headers.get('Location') || '').to.include('/staff-records/' + pm.collectionVariables.get('ncrId') + '/'));",
         ]),
    item("12. GET detail - back to Open", "GET", "/staff-records/{{ncrId}}/",
         tests=[
             "pm.test('Status badge is back to Open', () =>",
             "  pm.expect(pm.response.text()).to.match(/NCR-\\d{4}-\\d{4}<\\/span>\\s*<span class=\"badge badge-open\">\\s*Open/));",
         ]),
    item("13. POST edit NCR (change subject)", "POST", "/staff-records/{{ncrId}}/edit/",
         headers=[CSRF_HDR], follow=False,
         body=ue([("project", "{{projectId}}"), ("department", "{{departmentId}}"),
                  ("package_no", "PKG-{{uniq}}"), ("cause", "material"),
                  ("subject", "Integration NCR {{uniq}} - EDITED"),
                  ("issued_date", "2026-01-15"), ("required_date", "2026-02-15"),
                  ("description", "Edited by the integration suite")]),
         tests=["pm.test('Edit redirects (302)', () => pm.expect(pm.response.code).to.eql(302));"]),
    item("14. GET detail - edited subject visible", "GET", "/staff-records/{{ncrId}}/",
         tests=["pm.test('Edited subject visible', () => pm.expect(pm.response.text()).to.include('EDITED'));"]),
    item("15. GET search filter matches created NCR", "GET", "/staff-records/?q=Integration NCR {{uniq}}",
         tests=[
             "pm.test('Filtered list 200', () => pm.expect(pm.response.code).to.eql(200));",
             "pm.test('Created NCR matches search', () =>",
             "  pm.expect(pm.response.text()).to.include('Integration NCR ' + pm.collectionVariables.get('uniq')));",
         ]),
    item("16. POST export Excel", "POST", "/staff/export/", headers=[CSRF_HDR],
         body=fd([("export_type", "excel"), ("columns", "reference_no"), ("columns", "subject"),
                  ("columns", "project"), ("columns", "cause"), ("columns", "status")]),
         tests=[
             "pm.test('Export returns 200', () => pm.expect(pm.response.code).to.eql(200));",
             "pm.test('Response is an xlsx file', () =>",
             "  pm.expect(pm.response.headers.get('Content-Type') || '').to.include('spreadsheetml'));",
             "pm.test('Sent as attachment', () =>",
             "  pm.expect(pm.response.headers.get('Content-Disposition') || '').to.include('attachment'));",
             "pm.test('Body is a non-empty xlsx (PK zip signature)', () => {",
             "  pm.expect(pm.response.text().slice(0, 2)).to.eql('PK');",
             "  pm.expect(Number(pm.response.headers.get('X-Export-Records'))).to.be.at.least(1);",
             "  pm.expect(pm.response.headers.get('X-Export-Filename') || '').to.match(/\\.xlsx$/);",
             "});",
         ]),
    item("17. POST export invalid format -> 400", "POST", "/staff/export/", headers=[CSRF_HDR],
         body=ue([("export_type", "bogus")]),
         tests=[
             "pm.test('Invalid export type rejected (400)', () => pm.expect(pm.response.code).to.eql(400));",
             "pm.test('JSON error returned', () => pm.expect(pm.response.text()).to.include('Choose a valid export format'));",
         ]),
    item("18. POST logout (staff)", "POST", "/logout/", headers=[CSRF_HDR], follow=False,
         tests=["pm.test('Logout redirects', () => pm.expect([200, 302]).to.include(pm.response.code));"]),
]


# ---------------------------------------------------------------- 6. Authorization & negative cases
int_authz = [
    item("1. POST login with a wrong password is rejected", "POST", "/login/", headers=[CSRF_HDR],
         follow=False,
         body=ue([("username", "{{adminEmail}}"), ("password", "definitely-not-the-password")]),
         tests=[
             "pm.test('Re-renders the login form (200, not a redirect)', () =>",
             "  pm.expect(pm.response.code).to.eql(200));",
             "pm.test('No session issued', () => pm.expect(!!pm.cookies.get('sessionid')).to.be.false);",
             "pm.test('Error message shown', () =>",
             "  pm.expect(pm.response.text()).to.include('Incorrect email or password'));",
             "pm.test('Still on the login form', () =>",
             "  pm.expect(pm.response.text()).to.include('name=\"username\"'));",
         ],
         desc="Negative auth: a bad password must never create a session."),
    item("2. Anonymous GET /admin-projects/ is sent to login", "GET", "/admin-projects/", follow=False,
         tests=[
             "pm.test('Not served anonymously (302)', () => pm.expect(pm.response.code).to.eql(302));",
             "pm.test('Redirected to login with ?next=', () => {",
             "  const loc = pm.response.headers.get('Location') || '';",
             "  pm.expect(loc).to.include('/login/');",
             "  pm.expect(loc).to.include('next=');",
             "});",
         ]),
    item("3. Anonymous GET /staff-records/ is sent to login", "GET", "/staff-records/", follow=False,
         tests=[
             "pm.test('Not served anonymously (302)', () => pm.expect(pm.response.code).to.eql(302));",
             "pm.test('Redirected to login', () =>",
             "  pm.expect(pm.response.headers.get('Location') || '').to.include('/login/'));",
         ]),
    item("4. POST /logout/ (reset)", "POST", "/logout/", headers=[CSRF_HDR], follow=False,
         tests=["pm.test('Logout tolerated', () => pm.expect([200, 302, 403]).to.include(pm.response.code));"]),
    item("5. POST login as STAFF (for the role-isolation checks)", "POST", "/login/", headers=[CSRF_HDR],
         follow=False,
         body=ue([("username", "{{staffEmail}}"), ("password", "{{staffPassword}}")]),
         tests=[
             "pm.test('Staff session established', () => pm.expect(pm.response.code).to.eql(302));",
             "pm.test('sessionid cookie issued', () => pm.expect(!!pm.cookies.get('sessionid')).to.be.true);",
         ]),
    item("6. Staff cannot open admin-only pages", "GET", "/admin-users/", follow=False,
         tests=[
             "pm.test('Admin page not served to staff', () => pm.expect(pm.response.code).to.not.eql(200));",
             "pm.test('Sent back to the staff dashboard', () =>",
             "  pm.expect(pm.response.headers.get('Location') || '').to.match(/staff-dashboard|staff\\/dashboard/));",
         ],
         desc="core.decorators.admin_required redirects a wrong-role user to their own dashboard."),
    item("7. Staff cannot list projects", "GET", "/admin-projects/", follow=False,
         tests=[
             "pm.test('Denied (403 from project_views or 302 from core.decorators)', () =>",
             "  pm.expect([302, 403]).to.include(pm.response.code));",
         ],
         desc="administration/project_views.py has its own admin_required that raises PermissionDenied (403), while core.decorators redirects (302)."),
    item("8. Staff cannot create a project", "POST", "/admin-projects/add/", headers=[CSRF_HDR], follow=False,
         body=ue([("project_name", "Should Not Exist"), ("client_name", "Hack"),
                  ("project_code", "HACK-{{uniq}}"), ("description", "unauthorised")]),
         tests=[
             "pm.test('Project was not created (never a 2xx)', () =>",
             "  pm.expect(pm.response.code).to.not.eql(200));",
             "pm.test('Denied with 403 (project_views) or redirected (core.decorators)', () =>",
             "  pm.expect([302, 403]).to.include(pm.response.code));",
         ]),
    item("9. Staff export as PDF without choosing an NCR is rejected", "POST", "/staff/export/",
         headers=[CSRF_HDR],
         body=ue([("export_type", "pdf")]),
         tests=[
             "pm.test('Rejected with 400', () => pm.expect(pm.response.code).to.eql(400));",
             "pm.test('Explains the missing NCR', () =>",
             "  pm.expect(pm.response.text()).to.include('Select an NCR to export'));",
         ]),
    item("10. Staff export as Excel with no columns is rejected", "POST", "/staff/export/",
         headers=[CSRF_HDR],
         body=ue([("export_type", "excel")]),
         tests=[
             "pm.test('Rejected with 400', () => pm.expect(pm.response.code).to.eql(400));",
             "pm.test('Explains the missing columns', () =>",
             "  pm.expect(pm.response.text()).to.include('Select at least one column'));",
         ]),
    item("11. POST /logout/ (reset)", "POST", "/logout/", headers=[CSRF_HDR], follow=False,
         tests=["pm.test('Logout tolerated', () => pm.expect([200, 302, 403]).to.include(pm.response.code));"]),
    item("12. POST login as ADMIN (for the mirror checks)", "POST", "/login/", headers=[CSRF_HDR],
         follow=False,
         body=ue([("username", "{{adminEmail}}"), ("password", "{{adminPassword}}")]),
         tests=[
             "pm.test('Admin session established', () => pm.expect(pm.response.code).to.eql(302));",
             "pm.test('Session issued', () => pm.expect(!!pm.cookies.get('sessionid')).to.be.true);",
         ]),
    item("13. Admin cannot open the staff records page", "GET", "/staff-records/", follow=False,
         tests=[
             "pm.test('Staff page not served to admin', () => pm.expect(pm.response.code).to.not.eql(200));",
             "pm.test('Sent to an admin dashboard', () =>",
             "  pm.expect(pm.response.headers.get('Location') || '').to.match(/admin-dashboard|reports\\/admin\\/dashboard/));",
         ]),
    item("14. Admin cannot use the staff export endpoint", "GET", "/staff/export/", follow=False,
         tests=[
             "pm.test('Staff export not served to admin', () => pm.expect(pm.response.code).to.not.eql(200));",
             "pm.test('Sent to an admin dashboard', () =>",
             "  pm.expect(pm.response.headers.get('Location') || '').to.match(/admin-dashboard|reports\\/admin\\/dashboard/));",
         ]),
    item("15. POST /logout/ (leave the collection signed out)", "POST", "/logout/", headers=[CSRF_HDR],
         follow=False,
         tests=["pm.test('Logged out', () => pm.expect([200, 302]).to.include(pm.response.code));"]),
]

collection["item"] = [
    {"name": "1. Admin session & dashboards", "item": int_admin},
    {"name": "2. Projects CRUD chain", "item": int_projects},
    {"name": "3. Departments CRUD chain", "item": int_departments},
    {"name": "4. Logout & session invalidation", "item": int_logout},
    {"name": "5. Staff NCR lifecycle", "item": int_ncr},
    {"name": "6. Authorization & negative cases", "item": int_authz},
]

path = os.path.join(OUT, "ARKCafe-Integration.postman_collection.json")
json.dump(collection, open(path, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
print("written:", path)
