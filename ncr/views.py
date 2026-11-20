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


# ------------------------------------------------------------ NCR Records
@staff_required
def staff_records(request):
    qs = NcrRecord.objects.select_related("project", "department", "created_by").order_by("-ncr_id")
    g = request.GET

    q = (g.get("q") or "").strip()
    if q:
        qs = qs.filter(
            Q(reference_no__icontains=q) | Q(subject__icontains=q) | Q(package_no__icontains=q)
            | Q(project__project_name__icontains=q) | Q(project__project_code__icontains=q)
        )
    if g.get("status") in dict(NcrRecord.STATUS_CHOICES):
        qs = qs.filter(status=g["status"])
    if g.get("cause") in dict(NcrRecord.CAUSE_CHOICES):
        qs = qs.filter(cause=g["cause"])
    if (g.get("project") or "").isdigit():
        qs = qs.filter(project_id=int(g["project"]))
    if (g.get("department") or "").isdigit():
        qs = qs.filter(department_id=int(g["department"]))
    for param, lookup in (("date_from", "issued_date__gte"), ("date_to", "issued_date__lte")):
        value = g.get(param)
        if value:
            try:
                qs = qs.filter(**{lookup: timezone.datetime.fromisoformat(value).date()})
            except ValueError:
                pass

    page = Paginator(qs, 10).get_page(g.get("page"))
    params = g.copy()
    params.pop("page", None)
    return render(request, "ncr/records.html", {
        "page_obj": page,
        "querystring": params.urlencode(),
        "filters": g,
        "today": timezone.localdate(),
        "open_statuses": NcrRecord.OPEN_STATUSES,
        "status_choices": NcrRecord.STATUS_CHOICES,
        "cause_choices": NcrRecord.CAUSE_CHOICES,
        "projects": Project.objects.order_by("project_name"),
        "departments": Department.objects.order_by("department_name"),
    })


# ------------------------------------------------------------ Create NCR
@staff_required
def staff_create_ncr(request):
    if request.method == "POST":
        form = NcrForm(request.POST, request.FILES)
        if form.is_valid():
            ncr = services.create_ncr(form, request.user)
            messages.success(
                request, f"{ncr.reference_no} was created successfully", extra_tags="NCR created"
            )
            return redirect("ncr_detail", pk=ncr.pk)
    else:
        form = NcrForm()
    return render(request, "ncr/ncr_form.html", {"form": form, "ncr": None})


# ------------------------------------------------------------ NCR Details (+ Update Status)
@staff_required
def ncr_detail(request, pk):
    ncr = get_object_or_404(
        NcrRecord.objects.select_related("project", "department", "created_by"), pk=pk
    )
    if request.method == "POST":
        status_form = StatusUpdateForm(request.POST, ncr=ncr)
        if status_form.is_valid():
            d = status_form.cleaned_data
            services.change_status(
                ncr, request.user, d["new_status"],
                d["resolution_type"], d["resolution_note"], d["remarks"],
            )
            messages.success(
                request, f"{ncr.reference_no} is now {ncr.get_status_display()}",
                extra_tags="Status updated",
            )
            return redirect("ncr_detail", pk=ncr.pk)
    else:
        status_form = StatusUpdateForm(ncr=ncr)

    return render(request, "ncr/ncr_detail.html", {
        "ncr": ncr,
        "status_form": status_form,
        "attachments": ncr.attachments.defer("file_data").order_by("uploaded_at"),
        "history": ncr.audit_entries.select_related("user").order_by("-changed_at", "-history_id"),
        "today": timezone.localdate(),
        "open_statuses": NcrRecord.OPEN_STATUSES,
    })


# ------------------------------------------------------------ Edit NCR
@staff_required
def ncr_edit(request, pk):
    ncr = get_object_or_404(NcrRecord, pk=pk)
    if request.method == "POST":
        form = NcrForm(request.POST, request.FILES, instance=ncr)
        if form.is_valid():
            services.update_ncr(form, request.user)
            messages.success(
                request, "Your edit was saved successfully", extra_tags="NCR updated"
            )
            return redirect("ncr_detail", pk=ncr.pk)
    else:
        form = NcrForm(instance=ncr)
    return render(request, "ncr/ncr_form.html", {
        "form": form,
        "ncr": ncr,
        "attachments": ncr.attachments.defer("file_data").order_by("uploaded_at"),
    })


# ------------------------------------------------------------ Attachments
@staff_required
def ncr_attachment(request, pk, attachment_id):
    att = get_object_or_404(Attachment, pk=attachment_id, ncr_id=pk)
    response = FileResponse(
        io.BytesIO(bytes(att.file_data)),
        as_attachment=True,
        filename=att.file_name,
        content_type=att.file_type or "application/octet-stream",
    )
    response["X-Content-Type-Options"] = "nosniff"
    return response


@staff_required
@require_POST
def ncr_attachment_delete(request, pk, attachment_id):
    att = get_object_or_404(Attachment, pk=attachment_id, ncr_id=pk)
    ncr = att.ncr
    name = att.file_name
    att.delete()
    hooks.log_activity(
        request.user, "update", "ncr", ncr.pk, ncr.reference_no,
        new_value=f"Removed attachment: {name}"[:255],
    )
    messages.success(request, f"{name} was removed", extra_tags="Attachment removed")
    return redirect("ncr_edit", pk=ncr.pk)