"""Build the SMS text for each NCR event.

Kept separate from delivery so the wording can be changed in one place.
"""

from __future__ import annotations

from django.conf import settings

from core.models import NcrRecord

# Keep messages short: one long SMS is split into several billable segments.
MAX_LENGTH = 480


def _prefix() -> str:
    prefix = getattr(settings, "TEXTBEE_MESSAGE_PREFIX", "[NCR]")
    return f"{prefix} " if prefix else ""


def _clean(value: str | None) -> str:
    """Collapse whitespace so a multi-line textarea fits on one SMS line."""
    return " ".join(str(value or "").split())


def _fit(lines: list[str]) -> str:
    message = "\n".join(line for line in lines if line)
    if len(message) <= MAX_LENGTH:
        return message
    return message[: MAX_LENGTH - 3].rstrip() + "..."


def _reference(ncr: NcrRecord) -> str:
    project_code = getattr(ncr.project, "project_code", "")
    return f"{ncr.reference_no} ({project_code})" if project_code else ncr.reference_no


def ncr_created_message(ncr: NcrRecord) -> str:
    """New NCR: subject and cause."""
    return _fit([
        f"{_prefix()}New {_reference(ncr)}",
        f"Subject: {_clean(ncr.subject)}",
        f"Cause: {ncr.get_cause_display()}",
        f"Description: {_clean(ncr.description)}",
    ])


def ncr_status_message(
    ncr: NcrRecord,
    old_status: str,
    new_status: str,
    remarks: str = "",
) -> str:
    """Status update: remarks for in progress, plus type and note when resolved."""
    status_label = dict(NcrRecord.STATUS_CHOICES).get(new_status, new_status)
    lines = [f"{_prefix()}{_reference(ncr)} is now {status_label}."]

    if new_status == NcrRecord.STATUS_RESOLVED:
        resolution_type = ncr.get_resolution_type_display()
        if resolution_type:
            lines.append(f"Resolution type: {resolution_type}")
        if _clean(ncr.resolution_note):
            lines.append(f"Resolution note: {_clean(ncr.resolution_note)}")

    if _clean(remarks):
        lines.append(f"Remarks: {_clean(remarks)}")

    if len(lines) == 1:  # never send a bare status line
        lines.append(f"Changed from {dict(NcrRecord.STATUS_CHOICES).get(old_status, old_status)}.")

    return _fit(lines)
