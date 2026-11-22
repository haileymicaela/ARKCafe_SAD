<div align="center">

# Crimson NCR Tracking System

### User Manual

**Team 5**

![Python](https://img.shields.io/badge/Python-3.12%2B-3776AB?logo=python&logoColor=white)
![Django](https://img.shields.io/badge/Django-6.1-092E20?logo=django&logoColor=white)
![Database](https://img.shields.io/badge/PostgreSQL-4169E1?logo=postgresql&logoColor=white)

A web-based Non-Conformance Report (NCR) tracking system for QA/QC teams.<br>
It centralizes NCR reporting, status tracking, audit history, exports, and SMS alerts in one place.

</div>

---

## Contents

- [Overview](#overview)
- [Getting Started](#getting-started)
- [Signing In](#signing-in)
- [Admin Guide](#admin-guide)
- [Staff Guide](#staff-guide)
- [NCR Lifecycle](#ncr-lifecycle)
- [SMS Alerts](#sms-alerts)
- [Reference](#reference)
- [Troubleshooting](#troubleshooting)
- [Project Structure](#project-structure)

---

## Overview

The system replaces spreadsheet-based NCR tracking with a shared workflow for
admins and QA/QC staff.

| Capability | Description |
|---|---|
| **NCR records** | Create, search, filter, edit, and track every NCR |
| **Status workflow** | Open → In Progress → Resolved, with reopening support |
| **Audit trail** | Every status change keeps the user, timestamp, and remarks |
| **Attachments** | Photos and documents attached to each NCR |
| **SMS alerts** | TextBee notifications on creation and status updates |
| **Dashboards** | Open/closed totals, resolution rate, cause and project charts |
| **Exports** | Filtered NCR list to Excel; single NCR report to PDF |
| **Access control** | Separate Admin and QA/QC Staff roles and menus |

### Roles

| Role | Main responsibilities |
|---|---|
| **Admin** | Manage projects, departments, user accounts, and alert recipients. View dashboards, audit history, and activity. |
| **Staff (QA/QC)** | Create and manage NCRs, update statuses, manage alert recipients, view dashboards and audit history, export reports. |

> [NOTE]
> Admins cannot open staff-only pages and staff cannot open
> admin-only pages. Each role is redirected to its own dashboard.

---

## Signing In

1. Open <https://ncr-tracking-system.onrender.com/login/>.
2. Enter your email address and password.
3. You are redirected automatically:
   - **Admin** → Admin Dashboard
   - **Staff** → Staff Dashboard

Email addresses are not case-sensitive. Inactive accounts cannot sign in.

To sign out, use **Log Out** at the bottom of the sidebar. Logging out always
returns you to the login page.

> [TIP]
> **Forgot your password?** There is no self-service reset. Ask an administrator
> to reset it from **User Accounts**.

---

## Admin Guide

### Dashboard

The dashboard summarizes the current workload:

- Total **Open** and **Resolved** NCRs
- Resolution rate
- NCRs grouped by cause
- NCRs grouped by project
- Recent activity feed

### Projects

Use **Projects** to maintain the list of projects available when creating an
NCR.

| Action | How |
|---|---|
| **Add** | Select **Add Project**, fill in name, client, code, and description |
| **Search** | Use the search box by project name, code, or client |
| **Edit** | Open the project's **Edit** action and save changes |
| **Delete** | Use **Delete** on the project row |

> [NOTE]
> A project that is already linked to NCR records cannot be deleted.
> NCRs must be reassigned or the project left in place.

### Departments

Departments identify the responsible team for an NCR and the home department of
alert recipients.

| Action | How |
|---|---|
| **Add** | Select **Add Department** and enter a unique name |
| **Rename** | Use the **Rename** action on a department |
| **Delete** | Use **Delete** on the department row |

Duplicate names are rejected, regardless of capitalization. A department that
is still used by recipients or NCR records cannot be deleted.

### User Accounts

Manage Admin and Staff accounts from this page.

| Action | How |
|---|---|
| **Add** | Select **Add User**, then enter name, email, department, role, and password |
| **Edit** | Change name, email, department, role, or active status |
| **Reset password** | Set a new password for the user |
| **Deactivate** | Prevent the user from signing in without deleting the account |
| **Delete** | Permanently remove an account with no records |

Rules enforced by the system:

- Email addresses must be unique.
- Password confirmation must match.
- You cannot deactivate or demote your own account.
- You cannot delete your own account.
- A user with existing NCRs or activity records cannot be deleted. Deactivate
  the account instead.

### Alert Recipients

Alert Recipients are the people who receive SMS alerts.

| Field | Notes |
|---|---|
| **Name** | Recipient's display name |
| **Mobile number** | 11 digits, for example `09171234567` |
| **Department** | Department the recipient belongs to |

Use **Add Recipient**, **Edit**, or **Delete** on the page.

> [IMPORTANT]
> **Current behavior:** every NCR alert is sent to **all** Alert Recipients,
> regardless of the NCR's department. Each unique number receives one SMS per
> event.

### Audit History

The admin **Audit History** page lists every NCR status change.

You can:

- Search by NCR reference, user name, or remarks
- Filter by status and date range
- Sort newest or oldest first
- Move through pages of 10 entries

Each entry shows the NCR, old and new status, the user, the remarks, and the
date and time of the change.

---

## Staff Guide

### Dashboard

The staff dashboard shows the same operational summary as the admin dashboard:

- Open and resolved NCR counts
- Resolution rate
- Cause and project charts
- Recent activity

### NCR Records

**NCR Records** is the main working list.

| Feature | Description |
|---|---|
| **Search** | Search by NCR number, subject, package number, project name, or project code |
| **Filters** | Filter by project, cause, status, and date raised |
| **Sort** | Switch between newest first and oldest first |
| **Days open** | Days since the NCR was raised (hidden for resolved NCRs) |
| **Pagination** | 10 NCRs per page |

Select any row to open the NCR detail page.

> [NOTE]
> All staff accounts can view all NCR records. Visibility is shared
> across the QA/QC team rather than limited to the creator.

### Creating an NCR

Select **Create NCR** and complete the form.

| Field | Required | Notes |
|---|:---:|---|
| **Project** | Yes | Project the NCR belongs to |
| **Package No.** | No | Example: `PKG-114` |
| **Reference No.** | Auto | Generated when saved, for example `NCR-2026-0001` |
| **Issued date** | Auto | Set to today's date |
| **Subject** | Yes | Short summary of the non-conformance |
| **Cause** | Yes | Material, Workmanship, or Sequencing |
| **Department** | Yes | Responsible department |
| **Required date** | Yes | Cannot be earlier than the issued date |
| **Description** | No | What was found, where, and which specification was affected |
| **Attachments** | No | Up to 15 files, maximum 5 MB each |

Allowed attachment types: PDF, PNG, JPG/JPEG, Word, and Excel.

When the NCR is saved:

- Status is set to **Open**
- A reference number is generated
- An audit entry and activity entry are created
- An SMS alert is sent if SMS is enabled

### NCR Detail

The detail page shows:

- Reference number, status, and subject
- Project, package, department, and dates
- Cause and description
- Resolution details when resolved
- Attachments
- Full status history with remarks

From this page you can **Edit NCR**, **Update Status**, or **Export NCR**.

### Updating status

Select **Update Status** to open the status form.

| New status | What to provide |
|---|---|
| **In Progress** | Remarks describing the action taken |
| **Resolved** | Resolution type, resolution date, resolution note, and remarks |
| **Open** | Only when reopening a resolved NCR; remarks explain why |

**Resolution types:**

| Type | Meaning |
|---|---|
| **Replaced** | The non-conforming item was replaced |
| **Reapproved** | The item was accepted after review or rework |
| **Closed** | The NCR is closed without replacement |

A resolved NCR can be reopened. Reopening clears the previous resolution type,
note, and date.

### Attachments

- Download an attachment by selecting its file name.
- Delete an attachment while editing the NCR.
- Each file must be 5 MB or smaller.
- Up to 15 files can be uploaded at a time.
- Only PDF, image, Word, and Excel files are accepted.

### Export

Open **Export** from the sidebar. Two formats are available.

#### NCR List (Excel)

1. Choose the filters: project, package number, cause, status, and date range.
2. Select at least one column to include.
3. Select **Export to Excel**.

The file is named `NCR-List_<date>.xlsx` and contains only the matching records.

Available columns:

`NCR No.`, `Subject`, `Project`, `Package No.`, `Cause`, `Status`,
`Date Raised`, `Date Resolved`, `Days Open`, `Department`, `Created By`.

#### Single NCR (PDF)

1. Select the **Single NCR (PDF)** tab.
2. Choose an NCR.
3. Optionally include attachments, status history, and resolution details.
4. Select **Export to PDF**.

The file is named after the NCR reference, for example `NCR-2026-0001.pdf`.

### Audit History

Staff can search and filter the same NCR audit history as admins:

- Search by NCR reference, user, or remarks
- Filter by status and date range
- Sort newest or oldest first

### Alert Recipients

Staff can also view and maintain **Alert Recipients** from the sidebar. Add,
edit, or remove recipients and their 11-digit mobile numbers. Every recipient
receives NCR alerts when SMS is enabled.

---

## NCR Lifecycle

### Status definitions

| Status | Meaning |
|---|---|
| **Open** | The NCR has been raised and is awaiting action |
| **In Progress** | Work to correct the non-conformance has started |
| **Resolved** | The non-conformance has been corrected and documented |

### Allowed transitions

| From | To | Notes |
|---|---|---|
| Open | In Progress | Start work and add remarks |
| Open | Resolved | Resolve directly, with resolution details |
| In Progress | Resolved | Complete the work and record the resolution |
| Resolved | Open | Reopen if the issue returns |

Every transition creates an audit entry. Status changes also send an SMS alert
when SMS is enabled.

---

## SMS Alerts

### When alerts are sent

| Event | Message contents |
|---|---|
| **New NCR** | Reference, subject, cause, description |
| **Status → In Progress** | Reference, new status, remarks |
| **Status → Resolved** | Reference, new status, resolution type, resolution note, remarks |
| **Status → Open (reopened)** | Reference, new status, remarks |

Example new-NCR message:

```text
[NCR] New NCR-2026-0001 (PRJ-001)
Subject: Cracked weld on column C4
Cause: Workmanship
Description: Weld toe crack found during visual inspection
```

### Who receives alerts

By default, every number on the **Alert Recipients** page receives each alert.
If the same number appears more than once, it is only sent once.

### Delivery behavior

- Messages are sent after the NCR is saved successfully.
- A failed SMS never blocks or rolls back an NCR save.
- Failures are written to the server log.
- There is no automatic retry; a failed message is not sent later.
- Each recipient counts as one message against the TextBee plan limit.
- When the TextBee quota is exhausted, NCRs still work normally.

---

## Reference

### NCR fields

| Field | Description |
|---|---|
| **Reference No.** | Auto-generated unique NCR number |
| **Project** | Project where the non-conformance was found |
| **Package No.** | Optional package identifier |
| **Subject** | Short NCR title |
| **Description** | Detailed description of the issue |
| **Cause** | Material, Workmanship, or Sequencing |
| **Department** | Responsible department |
| **Status** | Open, In Progress, or Resolved |
| **Resolution type** | Replaced, Reapproved, or Closed |
| **Resolution note** | Explanation of how the issue was resolved |
| **Issued date** | Date the NCR was raised |
| **Required date** | Target completion date |
| **Resolve date** | Date the NCR was resolved |

### Cause definitions

| Cause | Typical meaning |
|---|---|
| **Material** | Deviates from the approved specification or uses an unapproved equivalent |
| **Workmanship** | Finishing or punch-list defect |
| **Sequencing** | Surface closed before MEP trades finished |

### File limits

| Rule | Value |
|---|---|
| Maximum file size | 5 MB per file |
| Maximum files per upload | 15 |
| Allowed extensions | `.pdf`, `.png`, `.jpg`, `.jpeg`, `.doc`, `.docx`, `.xls`, `.xlsx` |

---

## Troubleshooting

### I cannot sign in

- Check that the email address is correct. It is not case-sensitive.
- Confirm the account is active. An admin can reactivate it from **User Accounts**.
- Ask an admin to reset your password if necessary.
- Staff and Admin accounts are separate roles; each lands on its own dashboard.

### I am redirected when opening a page

This is expected. Admins cannot open staff-only pages, and staff cannot open
admin-only pages. Use the sidebar for your role.

### SMS is not received

Check the following in order:

1. **Recipients exist** — the Alert Recipients page has at least one entry.
2. **The phone has SMS permission and load** — the SIM can send normal texts.
3. **The quota is not exhausted** — TextBee shows the remaining plan limit.

If a recipient is missing from the list, no message is sent to that person.

### Export fails

- **Excel:** select at least one column.
- **PDF:** select an NCR first.
- **No records:** widen the date range or clear filters.
- **Unexpected format error:** choose either Excel or PDF, not a custom value.

---

<div align="center">

**Crimson NCR Tracking System** — Team 5

</div>