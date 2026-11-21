from functools import wraps

from django.contrib import messages
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import ProtectedError, Q
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST

from core.models import Project
from core.helpers import log_activity
from .project_forms import ProjectForm


# Pansamantalang decorator. Kung may sarili ka nang admin_required
# (sa user_views.py o accounts), burahin ito at i-import ang sa'yo.
def admin_required(view):
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())
        role = str(getattr(request.user, "role", "")).lower()
        if role != "admin" and not request.user.is_superuser:
            raise PermissionDenied
        return view(request, *args, **kwargs)
    return wrapper


def count_ncrs(project):
    """Bilang ng NCR records na naka-link sa project.

    Hinahanap nito ang reverse relation galing sa model na may 'ncr'
    sa pangalan, kaya hindi kailangang alam ang related_name sa core.
    Magbabalik ng 0 kung wala pang NCR model.
    """
    total = 0
    for rel in project._meta.related_objects:
        if "ncr" in rel.related_model.__name__.lower():
            manager = getattr(project, rel.get_accessor_name(), None)
            if manager is not None and hasattr(manager, "count"):
                total += manager.count()
    return total


def _render_list(request, form=None, modal_title=None, modal_action=None):
    q = request.GET.get("q", "").strip()
    qs = Project.objects.all().order_by("project_code")
    if q:
        qs = qs.filter(
            Q(project_name__icontains=q)
            | Q(project_code__icontains=q)
            | Q(client_name__icontains=q)
        )
    page = Paginator(qs, 10).get_page(request.GET.get("page"))

    # Para gumana ang {{ p.ncr_count }} sa template nang walang binabago
    for p in page:
        p.ncr_count = count_ncrs(p)

    return render(request, "administration/projects.html", {
        "page": page,
        "q": q,
        "total": qs.count(),
        "form": form or ProjectForm(),
        "modal_title": modal_title,
        "modal_action": modal_action,
    })


@admin_required
def project_list(request):
    return _render_list(request)


@admin_required
@require_POST
def project_add(request):
    form = ProjectForm(request.POST)
    if form.is_valid():
        p = form.save()
        log_activity(request.user, "create", "project", p.pk, p.project_name,
                     new_value=p.project_code)
        messages.success(
            request,
            f"{p.project_name} was added successfully",
            extra_tags="Project added",
        )
        return redirect("project_list")
    return _render_list(request, form, "Add Project", request.path)


@admin_required
@require_POST
def project_edit(request, pk):
    project = get_object_or_404(Project, pk=pk)
    form = ProjectForm(request.POST, instance=project)
    if form.is_valid():
        old_name = project.project_name
        old_code = project.project_code
        form.save()
        changed = ", ".join(form.changed_data)
        if changed:
            log_activity(request.user, "update", "project", project.pk, project.project_name,
                         old_value=f"{old_name} ({old_code})",
                         new_value=f"{project.project_name} ({project.project_code}; {changed})")
        messages.success(request, "Project updated.")
        return redirect("project_list")
    return _render_list(request, form, "Edit Project", request.path)


@admin_required
@require_POST
def project_delete(request, pk):
    project = get_object_or_404(Project, pk=pk)
    n = count_ncrs(project)
    if n:
        messages.error(
            request,
            f"Can't delete {project.project_code}: linked to {n} NCR records.",
        )
        return redirect("project_list")
    project_id = project.pk
    project_name = project.project_name
    try:
        project.delete()
        log_activity(request.user, "delete", "project", project_id, project_name,
                     old_value=project.project_code)
        messages.success(
            request,
            f"{project_name} was deleted successfully",
            extra_tags="Project deleted",
        )
    except ProtectedError:
        messages.error(
            request,
            f"Can't delete {project.project_code}: it is still referenced by other records.",
        )
    return redirect("project_list")
