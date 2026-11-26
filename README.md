<h1 align="center">Crimson NCR Tracking System</h1>

<p align="center">
  <strong>
    A web-based QA/QC platform for raising, tracking, and closing Non-Conformance Reports (NCRs), with audit history, SMS alerts, dashboards, and exports.
  </strong>
</p>

<p align="center">
  <a href="https://ncr-tracking-system.onrender.com">
    <strong>Live Website</strong>
  </a>
</p>

---

<a id="table-of-contents"></a>

# 📚 Table of Contents

- [About the Project](#about-the-project)
- [Key Features](#key-features)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
- [Demo Accounts - Live Website](#demo-accounts)
- [User Roles & Permissions](#user-roles--permissions)
- [Usage Guide](#usage-guide)
- [Route Overview](#route-overview)
- [Database](#database)
- [API Integration](#api-integration)
- [Security](#security)
- [Authors](#authors)
- [License](#license)

---

<a id="about-the-project"></a>

# 📖 About the Project

The **Crimson NCR Tracking System** is a full-stack web application developed for the **QA/QC Department of Crimson Group Incorporated**. It replaces spreadsheets, email threads, and paper forms with one auditable workflow covering the entire NCR lifecycle, from the moment an issue is raised to the moment it is resolved.

The system lets QA/QC staff create and update NCRs with file attachments, notifies responsible people by SMS, and gives administrators dashboards, audit history, and master-data management.

The platform implements **Role-Based Access Control (RBAC)** with dedicated menus and permissions for:

- `ADMIN`
- `STAFF` (QA/QC)

---

<a id="key-features"></a>

# ✨ Key Features

* Centralised NCR Records with search, filters, sorting, and pagination
* Auto-generated Reference Numbers (e.g. `NCR-2026-0001`)
* Status Workflow: Open → In Progress → Resolved, with reopening support
* Audit Trail of every status change (user, timestamp, remarks)
* File Attachments per NCR (PDF, images, Word, Excel)
* SMS Alerts to recipients through TextBee
* Role-Based Access Control (User Roles: Admin, Staff)
* Dashboards with open/resolved totals, resolution rate, and cause/project charts
* Exports: filtered NCR list to Excel, single NCR report to PDF
* Admin Management of projects, departments, user accounts, and alert recipients
* Activity Log for administrators
* Responsive Design (Compatible with both desktop and mobile device use)

---

<a id="tech-stack"></a>

# 🛠️ Tech Stack

| Layer | Technologies |
| --- | --- |
| Frontend | Django Templates, Bootstrap 5, Bootstrap Icons, vanilla JavaScript (SVG charts) |
| Backend | Django 6.1, Python 3.12+ |
| Database | PostgreSQL (SQLite for local development), `dj-database-url`, `psycopg2` |
| Authentication | Django custom user model (email login) + Role-Based Access |
| SMS | TextBee (Android SMS gateway) |
| Deployment | Render (web service + PostgreSQL), Gunicorn, WhiteNoise |
| CI/CD | GitHub Actions |
| Testing | Django test suite, Postman (E2E, integration, security) |
| Tools | Git, GitHub, VS Code |

---

<a id="project-structure"></a>

# 🗂️ Project Structure

```bash
main/
	config/
		settings.py
		urls.py
		wsgi.py
		asgi.py
	core/
		decorators.py
		helpers.py
		models.py
		static/
		templates/
			base.html
			admin_sidebar.html
			staff_sidebar.html
	accounts/
		models.py
		forms.py
		views.py
		urls.py
		templates/accounts/login.html
	ncr/
		forms.py
		hooks.py
		services.py
		views.py
		urls.py
		static/ncr/
		templates/ncr/
			records.html
			ncr_form.html
			ncr_detail.html
	administration/
		alert_views.py
		project_views.py
		user_views.py
		views.py
		urls.py
		templates/administration/
			alert_recipients.html
			departments.html
			projects.html
			users.html
	reports/
		views.py
		urls.py
		static/reports/
			css/
			js/
		templates/reports/
			dashboard.html
			audit_history.html
			recent_activity.html
			export_ncr.html
	notifications/
		textbee.py
		services.py
		messages.py
		management/commands/
			check_textbee.py
			send_test_sms.py
	postman/
		ARKCafe-E2E.postman_collection.json
		ARKCafe-Integration.postman_collection.json
		ARKCafe-Security.postman_collection.json
	.github/workflows/ci.yml
	.env.example
	manage.py
	requirements.txt
	API_Integration_Documentation.md
	user-manual.md
```

> The project follows a modular Django structure: shared models in `core`, one app per feature area, and templates and static files kept inside each app.

---

<a id="getting-started"></a>

# 🚀 Getting Started

## Prerequisites

Before running the project locally, make sure the following are installed:

- Python `3.12+`
- pip
- PostgreSQL (optional, SQLite is used when `DATABASE_URL` is not set)
- Git

---

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/haileymicaela/CrimsonCompany.git

cd CrimsonCompany
```

---

### 2. Create and Activate a Virtual Environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

---

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

---

### 4. Create Environment Variables

Copy the example file and fill in your values.

```bash
cp .env.example .env
```

Example:

```env
SECRET_KEY=
DEBUG=True
DATABASE_URL=

TEXTBEE_ENABLED=True
TEXTBEE_API_KEY=
TEXTBEE_DEVICE_ID=
```

> Do not commit real environment variables or API keys to GitHub. Set `TEXTBEE_DRY_RUN=True` to log messages instead of sending them while testing.

---

### 5. Run Database Migrations

```bash
python manage.py migrate
```

---

### 6. Create an Admin Account

```bash
python manage.py createsuperuser
```

---

### 7. Start the Development Server

```bash
python manage.py runserver
```

Open the application:

```bash
http://127.0.0.1:8000
```
> The root URL redirects to the login page, and signed-in users are sent to their role's dashboard.

---

<a id="demo-accounts"></a>

# 🔑 Demo Accounts - Live Website

| Email | Password | Role |
|---|---|---|
| admin@crimson.group | crimsonadmin1 | Admin |
| yvaine_deluna@crimson.group | crimsonstaff1 | Staff |
| tanya_sy@crimson.group | crimsonstaff1 | Staff |

---

# 👥 User Roles & Permissions
<a id="user-roles--permissions"></a>

| Feature / Access | ADMIN | STAFF |
| --- | --- | --- |
| Login Authentication | ✅ | ✅ |
| View Dashboard | ✅ | ✅ |
| View Audit History | ✅ | ✅ |
| Create / Edit NCRs | ❌ | ✅ |
| Update NCR Status | ❌ | ✅ |
| Manage Attachments | ❌ | ✅ |
| Export NCRs (Excel / PDF) | ❌ | ✅ |
| Manage Alert Recipients | ✅ | ✅ |
| Manage Projects | ✅ | ❌ |
| Manage Departments | ✅ | ❌ |
| Manage User Accounts | ✅ | ❌ |
| View Activity Log | ✅ | ❌ |

## Administrative Distinctions

- `ADMIN` manages master data (projects, departments, users) and oversees dashboards, audit history, and activity.
- `STAFF` (QA/QC) handles day-to-day NCR work: creating NCRs, updating statuses, and exporting reports.
- Each role is redirected to its own dashboard, and cannot open the other role's pages.

---

<a id="usage-guide"></a>

# 🧭 Usage Guide
> For detailed, step-by-step instructions, see the [User Manual](user-manual.md).

## Staff Workflow

1. Login using your email and password.
2. Open **Create NCR**, select the project, and fill in the subject, cause, department, and required date.
3. Attach supporting files (optional) and save. A reference number is generated and an SMS alert is sent.
4. Use **Update Status** on the NCR detail page as work progresses, adding remarks each time.
5. When resolved, record the resolution type, date, and note.
6. Export reports from **Export** (Excel list or single-NCR PDF).

## Admin Workflow

1. Login using an admin account.
2. Maintain **Projects**, **Departments**, and **User Accounts**.
3. Maintain **Alert Recipients** (11-digit mobile numbers).
4. Monitor the dashboard, audit history, and activity log.

## NCR Fields

| Field | Notes |
| --- | --- |
| Reference No. | Auto-generated (`NCR-<year>-<number>`) |
| Project / Package No. | Project is required; package number is optional |
| Subject | Short summary of the non-conformance |
| Cause | Material, Workmanship, or Sequencing |
| Department | Responsible department |
| Required Date | Cannot be earlier than the issued date |
| Attachments | Up to 15 files, 5 MB each (`.pdf`, `.png`, `.jpg`, `.jpeg`, `.doc`, `.docx`, `.xls`, `.xlsx`) |

---

<a id="route-overview"></a>

# 🔌 Route Overview

The application uses server-rendered Django views.

| Route Group | Description |
| --- | --- |
| `/login/`, `/logout/` | Authentication |
| `/staff-records/`, `/staff-create/` | NCR list, creation, detail, edit, and attachments |
| `/staff/dashboard/`, `/staff/audit-history/`, `/staff/export/` | Staff reports and exports |
| `/reports/admin/...` | Admin dashboard, audit history, and activity log |
| `/admin-projects/`, `/admin-departments/`, `/admin-users/` | Admin master-data management |
| `/admin-recipients/` | Alert recipient management |
| `/admin/` | Django admin site |

---

<a id="database"></a>

# 🗄️ Database

The system uses **PostgreSQL** hosted on **Render** in production, and SQLite for local development when `DATABASE_URL` is not set.

## Connection Details

| Setting | Value |
| --- | --- |
| Host | `dpg-dbsl2e6c6qcc739fm1eg-a.singapore-postgres.render.com` |
| Port | `5432` |
| Maintenance Database | `ncr_db_kppg` |
| Username | `ncr_db_kppg_user` |
| Password | `olbAS2GUuIhT4z59oSG1tVggMfqioSbx` |
| SSL Mode | `require` |

**Render External Database URL**
```bash
postgresql://ncr_db_kppg_user:olbAS2GUuIhT4z59oSG1tVggMfqioSbx@dpg-dbsl2e6c6qcc739fm1eg-a.singapore-postgres.render.com/ncr_db_kppg
```

> Connect with pgAdmin, DBeaver, or `psql`. Render requires SSL for external connections.

---

<a id="api-integration"></a>

# 🔗 API Integration

The system does not expose its own REST API. It consumes one external API, **[TextBee](https://textbee.dev)**, an Android SMS gateway, to send SMS alerts to alert recipients. All calls are made server-side from `notifications/textbee.py`, so the API key never reaches the browser.

**Base URL:** `https://api.textbee.dev/api/v1`

## When SMS Is Sent

| Event | Message contents |
| --- | --- |
| New NCR created | Reference, subject, cause, description |
| Status → In Progress | Reference, new status, remarks |
| Status → Resolved | Reference, new status, resolution type, resolution note, remarks |
| Status → Open (reopened) | Reference, new status, remarks |

By default, every unique number on the **Alert Recipients** page receives each alert. Set `TEXTBEE_NOTIFY_ALL_RECIPIENTS=False` to notify only recipients in the NCR's department.

## Endpoints Used

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `POST` | `/gateway/send-sms` | Sends an NCR alert through the registered Android phone |
| `GET` | `/gateway/devices` | Verifies the API key and lists devices (used by `check_textbee`) |

### `POST /gateway/send-sms`

**Headers**

| Header | Required | Description |
| --- | --- | --- |
| `x-api-key` | Yes | TextBee API key from the dashboard |
| `Content-Type` | Yes | `application/json` |

**Request Body**

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `recipients` | string[] | Yes | Numbers in international format, e.g. `+639171234567` |
| `message` | string | Yes | SMS content |
| `deviceId` | string | No | Sending phone; defaults to the account's default device |

**Example Request**

```bash
curl -X POST "https://api.textbee.dev/api/v1/gateway/send-sms" \
  -H "x-api-key: $TEXTBEE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "recipients": ["+639171234567"],
    "message": "[NCR] New NCR-2026-0001 (PRJ-001)\nSubject: Cracked weld on column C4\nCause: Workmanship"
  }'
```

**Example Response** (`200 OK`)

```json
{
  "data": {
    "success": true,
    "message": "SMS added to queue for processing",
    "smsBatchId": "66b1f2c3a4d5e6f7a8b9c0d2",
    "recipientCount": 1
  }
}
```

> A `200` response means TextBee queued the message, not that the carrier delivered it.

### Error Codes

| Code | Meaning |
| --- | --- |
| `400` | Invalid recipient, no enabled device, or message could not be pushed to the phone |
| `401` | API key is missing, invalid, or revoked |
| `404` | Device or resource not found |
| `429` | Plan limit reached; nothing was sent |

## Configuration

```env
TEXTBEE_ENABLED=True
TEXTBEE_API_KEY=txb_your_api_key_here
TEXTBEE_DEVICE_ID=your_device_id_here
```

| Variable | Description |
| --- | --- |
| `TEXTBEE_ENABLED` | Master switch; `False` skips sending |
| `TEXTBEE_API_KEY` | Authenticates requests to TextBee |
| `TEXTBEE_DEVICE_ID` | Selects the sending Android phone |
| `TEXTBEE_NOTIFY_ALL_RECIPIENTS` | `True` alerts every recipient; `False` limits alerts to the NCR's department |
| `TEXTBEE_DRY_RUN` | Logs messages instead of sending them |

## Behavior

- Local numbers (e.g. `09171234567`) are converted to `+639171234567` before sending.
- SMS is sent after the NCR is saved, so a failed SMS never blocks or rolls back an NCR.
- Failures are logged per recipient, and one bad number does not stop the others.
- There is no automatic retry.

Verify your setup with:

```bash
python manage.py check_textbee
python manage.py send_test_sms 09171234567
```

See `API_Integration_Documentation.md` for the full reference.

---

<a id="security"></a>

# 🛡️ Security

## Security Best Practices

- Never expose `.env` files publicly.
- Set a strong `SECRET_KEY` and `DEBUG=False` in production.
- Restrict admin credentials to authorized users only.
- Rotate sensitive credentials (including the TextBee API key) regularly.
- Use HTTPS in production deployments.

## Built-in Protections

- Passwords are hashed and validated with Django's password validators.
- Inactive accounts cannot sign in; admins cannot deactivate, demote, or delete themselves.
- Role-based decorators restrict every admin and staff page.
- CSRF protection is enabled on all forms.
- Attachments are limited by size and file type.

## Important Notice

> Demo or development credentials should never be reused in production environments.

---

<a id="authors"></a>

# 👨‍💻 Authors

| Name | Role |
| --- | --- |
| Diaz, Ashley P. | Fullstack Developer |
| Lumanglas, Hailey Micaela O. | Tech Lead, Scrum Master |
| Macawile, Ariyhanna Venice A. | Fullstack Developer |
| Ogania, Mycha Izlia B. | Quality Assurance Engineer |
| Suarez, Allyson S. | Fullstack Developer |

---

<a id="license"></a>

# 📄 License

This project is currently proprietary and is intended for academic use unless otherwise stated by the project owners.