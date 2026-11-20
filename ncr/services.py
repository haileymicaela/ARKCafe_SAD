import mimetypes
import os

from django.db import IntegrityError, transaction
from django.utils import timezone

from core.models import Attachment, AuditLog, NcrRecord

from . import hooks

# open -> in progress -> resolved ; a resolved NCR can be reopened
ALLOWED_TRANSITIONS = {
    NcrRecord.STATUS_OPEN: [NcrRecord.STATUS_IN_PROGRESS, NcrRecord.STATUS_RESOLVED],
    NcrRecord.STATUS_IN_PROGRESS: [NcrRecord.STATUS_RESOLVED],
    NcrRecord.STATUS_RESOLVED: [NcrRecord.STATUS_OPEN],
}


def allowed_next(status):
    return ALLOWED_TRANSITIONS.get(status, [])


def _next_reference(year):
    """NCR-<year>-0001, NCR-<year>-0002, ..."""
    prefix = f"NCR-{year}-"
    highest = 0
    for ref in NcrRecord.objects.filter(reference_no__startswith=prefix).values_list(
        "reference_no", flat=True
    ):
        try:
            highest = max(highest, int(ref.rsplit("-", 1)[1]))
        except (ValueError, IndexError):
            continue
    return f"{prefix}{highest + 1:04d}"


def save_attachments(ncr, files):
    for f in files:
        name = os.path.basename(f.name)[:255]
        file_type = (mimetypes.guess_type(name)[0] or f.content_type or "application/octet-stream")[:100]
        Attachment.objects.create(ncr=ncr, file_name=name, file_type=file_type, file_data=f.read())


def create_ncr(form, user):
    """Save a validated NcrForm as a new NCR with auto reference number."""
    ncr = form.save(commit=False)
    year = timezone.localdate().year
    for attempt in range(5):
        try:
            with transaction.atomic():
                ncr.pk = None
                ncr._state.adding = True
                ncr.created_by = user
                ncr.status = NcrRecord.STATUS_OPEN
                ncr.reference_no = _next_reference(year)
                ncr.save()
                save_attachments(ncr, form.cleaned_data.get("attachments") or [])
                AuditLog.objects.create(
                    ncr=ncr, user=user, old_status="",
                    new_status=ncr.status, remarks="NCR created",
                )
                hooks.log_activity(user, "create", "ncr", ncr.pk, ncr.reference_no)
                message = f"New NCR {ncr.reference_no} ({ncr.project.project_code}): {ncr.subject}"
                transaction.on_commit(lambda: hooks.notify_department(ncr, message))
            return ncr
        except IntegrityError:  # two people got the same number at once -> retry
            if attempt == 4:
                raise


def update_ncr(form, user):
    with transaction.atomic():
        ncr = form.save()
        save_attachments(ncr, form.cleaned_data.get("attachments") or [])
        if form.changed_data:
            hooks.log_activity(
                user, "update", "ncr", ncr.pk, ncr.reference_no,
                new_value=("Edited: " + ", ".join(form.changed_data))[:255],
            )
    return ncr


@transaction.atomic
def change_status(ncr, user, new_status, resolution_type="", resolution_note="", remarks=""):
    old = ncr.status
    if new_status not in allowed_next(old):
        raise ValueError(f"Cannot change {old} -> {new_status}")

    if new_status == NcrRecord.STATUS_RESOLVED:
        ncr.resolution_type = resolution_type
        ncr.resolution_note = resolution_note
        ncr.resolve_date = timezone.localdate()
    elif old == NcrRecord.STATUS_RESOLVED:  # reopening
        previous = ncr.get_resolution_type_display()
        if previous:
            remarks = f"Reopened (previous resolution: {previous}). {remarks}".strip()
        ncr.resolution_type = ""
        ncr.resolution_note = ""
        ncr.resolve_date = None

    ncr.status = new_status
    ncr.save(update_fields=["status", "resolution_type", "resolution_note", "resolve_date"])

    AuditLog.objects.create(
        ncr=ncr, user=user, old_status=old, new_status=new_status, remarks=remarks,
    )
    hooks.log_activity(
        user, "status_change", "ncr", ncr.pk, ncr.reference_no,
        old_value=old, new_value=new_status,
    )
    labels = dict(NcrRecord.STATUS_CHOICES)
    message = f"NCR {ncr.reference_no} status changed: {labels[old]} -> {labels[new_status]}"
    transaction.on_commit(lambda: hooks.notify_department(ncr, message))
    return ncr