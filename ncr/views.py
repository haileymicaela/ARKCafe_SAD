
import io

from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import FileResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from core.decorators import staff_required
from core.models import Attachment, Department, NcrRecord, Project

from . import hooks, services
from .forms import NcrForm, StatusUpdateForm


# ------------------------------------------------------------
# NCR Records
# ------------------------------------------------------------

@staff_required
def staff_records(request):
    qs = NcrRecord.objects.select_related(
        "project",
        "department",
        "created_by"
    )

    g = request.GET

    # Search
    q = (g.get("q") or "").strip()

    if q:
        qs = qs.filter(
            Q(reference_no__icontains=q)
            | Q(subject__icontains=q)
            | Q(package_no__icontains=q)
            | Q(project__project_name__icontains=q)
            | Q(project__project_code__icontains=q)
        )

    # Status filter
    active_filters = []
    status_labels = dict(NcrRecord.STATUS_CHOICES)
    status_value = g.get("status")
    if status_value in status_labels:
        qs = qs.filter(status=status_value)
        active_filters.append({"label": "Status", "value": status_labels[status_value], "key": "status"})

    # Cause filter
    cause_labels = dict(NcrRecord.CAUSE_CHOICES)
    cause_value = g.get("cause")
    if cause_value in cause_labels:
        qs = qs.filter(cause=cause_value)
        active_filters.append({"label": "Cause", "value": cause_labels[cause_value], "key": "cause"})

    # Project filter
    if (g.get("project") or "").isdigit():
        project = Project.objects.filter(pk=int(g["project"])).first()
        if project:
            qs = qs.filter(project_id=project.pk)
            active_filters.append({"label": "Project", "value": project.project_name, "key": "project"})

    # Department filter
    if (g.get("department") or "").isdigit():
        qs = qs.filter(department_id=int(g["department"]))

    # Date filters
    for param, lookup in (
        ("date_from", "issued_date__gte"),
        ("date_to", "issued_date__lte"),
    ):
        value = g.get(param)

        if value:
            try:
                parsed_date = timezone.datetime.fromisoformat(value).date()
                qs = qs.filter(
                    **{lookup: parsed_date}
                )
            except ValueError:
                pass

    date_from = None
    date_to = None
    try:
        if g.get("date_from"):
            date_from = timezone.datetime.fromisoformat(g["date_from"]).date()
    except ValueError:
        pass
    try:
        if g.get("date_to"):
            date_to = timezone.datetime.fromisoformat(g["date_to"]).date()
    except ValueError:
        pass
    if date_from or date_to:
        if date_from and date_to:
            date_label = f"{date_from:%b %d} – {date_to:%b %d, %Y}"
        elif date_from:
            date_label = f"From {date_from:%b %d, %Y}"
        else:
            date_label = f"Through {date_to:%b %d, %Y}"
        active_filters.append({"label": "Date", "value": date_label, "key": "date"})

    # Sorting
    sort = g.get("sort", "newest")

    if sort == "oldest":
        qs = qs.order_by("issued_date", "ncr_id")
    else:
        sort = "newest"
        qs = qs.order_by("-issued_date", "-ncr_id")

    # Current date
    today = timezone.localdate()

    # Pagination
    page = Paginator(qs, 10).get_page(g.get("page"))

    # Calculate Days Open for each NCR
    for ncr in page.object_list:

        if ncr.issued_date:
            ncr.days_open = max(
                (today - ncr.issued_date).days,
                0
            )
        else:
            ncr.days_open = None

    # Preserve query parameters for pagination
    params = g.copy()
    params.pop("page", None)
    clear_params = g.copy()
    for key in list(clear_params.keys()):
        if key not in ("q", "sort"):
            clear_params.pop(key, None)
    if q:
        clear_params["q"] = q
    clear_params["sort"] = sort
    for active_filter in active_filters:
        remove_params = g.copy()
        remove_params.pop("page", None)
        if active_filter["key"] == "date":
            remove_params.pop("date_from", None)
            remove_params.pop("date_to", None)
        else:
            remove_params.pop(active_filter["key"], None)
        active_filter["remove_url"] = "?" + remove_params.urlencode() if remove_params else "?sort=" + sort

    return render(request, "ncr/records.html", {
        "page_obj": page,
        "querystring": params.urlencode(),
        "filters": g,
        "active_filters": active_filters,
        "filter_count": len(active_filters),
        "clear_filters_url": "?" + clear_params.urlencode(),
        "sort": sort,
        "today": today,
        "open_statuses": NcrRecord.OPEN_STATUSES,
        "status_choices": NcrRecord.STATUS_CHOICES,
        "cause_choices": NcrRecord.CAUSE_CHOICES,
        "projects": Project.objects.order_by("project_name"),
        "departments": Department.objects.order_by("department_name"),
    })


# ------------------------------------------------------------
# Create NCR
# ------------------------------------------------------------

@staff_required
def staff_create_ncr(request):
    if request.method == "POST":
        form = NcrForm(request.POST, request.FILES)

        if form.is_valid():
            ncr = services.create_ncr(form, request.user)
            request.session["ncr_save_feedback"] = {"kind": "created", "ncr_id": ncr.pk}

            return redirect("ncr_detail", pk=ncr.pk)

    else:
        form = NcrForm()

    return render(request, "ncr/ncr_form.html", {
        "form": form,
        "ncr": None,
        "reference_preview": services.reference_preview(),
    })


# ------------------------------------------------------------
# NCR Details (+ Update Status)
# ------------------------------------------------------------

@staff_required
def ncr_detail(request, pk):
    ncr = get_object_or_404(
        NcrRecord.objects.select_related(
            "project",
            "department",
            "created_by"
        ),
        pk=pk
    )
    save_feedback = request.session.get("ncr_save_feedback")
    if save_feedback and save_feedback.get("ncr_id") == ncr.pk:
        request.session.pop("ncr_save_feedback", None)
    else:
        save_feedback = None

    if request.method == "POST":
        status_form = StatusUpdateForm(request.POST, ncr=ncr)

        if status_form.is_valid():
            d = status_form.cleaned_data

            services.change_status(
                ncr,
                request.user,
                d["new_status"],
                d["resolution_type"],
                d["resolution_note"],
                d["remarks"],
                d["resolve_date"],
            )

            messages.success(
                request,
                f"{ncr.reference_no} is now {ncr.get_status_display()}",
                extra_tags="Status updated"
            )

            return redirect("ncr_detail", pk=ncr.pk)

    else:
        status_form = StatusUpdateForm(ncr=ncr)

    return render(request, "ncr/ncr_detail.html", {
        "ncr": ncr,
        "status_form": status_form,
        "attachments": ncr.attachments.defer(
            "file_data"
        ).order_by("uploaded_at"),
        "history": ncr.audit_entries.select_related(
            "user"
        ).order_by("-changed_at", "-history_id"),
        "today": timezone.localdate(),
        "open_statuses": NcrRecord.OPEN_STATUSES,
        "save_feedback": save_feedback,
    })


# ------------------------------------------------------------
# Edit NCR
# ------------------------------------------------------------

@staff_required
def ncr_edit(request, pk):
    ncr = get_object_or_404(NcrRecord, pk=pk)

    if request.method == "POST":
        form = NcrForm(
            request.POST,
            request.FILES,
            instance=ncr
        )

        if form.is_valid():
            services.update_ncr(form, request.user)
            request.session["ncr_save_feedback"] = {"kind": "updated", "ncr_id": ncr.pk}

            return redirect("ncr_detail", pk=ncr.pk)

    else:
        form = NcrForm(instance=ncr)

    return render(request, "ncr/ncr_form.html", {
        "form": form,
        "ncr": ncr,
        "reference_preview": ncr.reference_no,
        "attachments": ncr.attachments.defer(
            "file_data"
        ).order_by("uploaded_at"),
    })


# ------------------------------------------------------------
# Attachments
# ------------------------------------------------------------

@staff_required
def ncr_attachment(request, pk, attachment_id):
    att = get_object_or_404(
        Attachment,
        pk=attachment_id,
        ncr_id=pk
    )

    response = FileResponse(
        io.BytesIO(bytes(att.file_data)),
        as_attachment=True,
        filename=att.file_name,
        content_type=att.file_type or "application/octet-stream",
    )

    response["X-Content-Type-Options"] = "nosniff"

    return response


# ------------------------------------------------------------
# Delete Attachment
# ------------------------------------------------------------

@staff_required
@require_POST
def ncr_attachment_delete(request, pk, attachment_id):
    att = get_object_or_404(
        Attachment,
        pk=attachment_id,
        ncr_id=pk
    )

    ncr = att.ncr
    name = att.file_name

    att.delete()

    hooks.log_activity(
        request.user,
        "update",
        "ncr",
        ncr.pk,
        ncr.reference_no,
        new_value=f"Removed attachment: {name}"[:255],
    )

    messages.success(
        request,
        f"{name} was removed",
        extra_tags="Attachment removed"
    )

    return redirect("ncr_edit", pk=ncr.pk)
