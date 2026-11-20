
from django.contrib import messages
from django.db.models import Count
from django.db.models.deletion import ProtectedError
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render

from core.decorators import admin_required
from core.models import Department

from .forms import DepartmentForm


@admin_required
def admin_departments(request):
    add_form = DepartmentForm(prefix="add")
    rename_form = DepartmentForm(prefix="rename")
    open_modal = None
    rename_id = None

    if request.method == "POST":
        action = request.POST.get("action")

        # Add Department
        if action == "add":
            add_form = DepartmentForm(request.POST, prefix="add")

            if add_form.is_valid():
                dept = add_form.save()

                messages.success(
                    request,
                    f"{dept.department_name} was added successfully",
                    extra_tags="Department added",
                )
                return redirect("admin_departments")

            open_modal = "add"

        # Rename Department
        elif action == "rename":
            try:
                rename_id = int(request.POST.get("department_id", ""))
            except (ValueError, TypeError):
                raise Http404

            dept = get_object_or_404(
                Department,
                pk=rename_id,
            )

            rename_form = DepartmentForm(
                request.POST,
                instance=dept,
                prefix="rename",
            )

            if rename_form.is_valid():
                rename_form.save()

                messages.success(
                    request,
                    "Your edit was saved successfully",
                    extra_tags="Department renamed",
                )
                return redirect("admin_departments")

            open_modal = "rename"

        # Delete Department
        elif action == "delete":
            try:
                department_id = int(
                    request.POST.get("department_id", "")
                )
            except (ValueError, TypeError):
                raise Http404

            dept = get_object_or_404(
                Department,
                pk=department_id,
            )

            department_name = dept.department_name

            try:
                dept.delete()

                messages.success(
                    request,
                    f"{department_name} was deleted successfully",
                    extra_tags="Department deleted",
                )

            except ProtectedError:
                messages.error(
                    request,
                    (
                        f"{department_name} cannot be deleted because "
                        "it is still being used by recipients or NCR records."
                    ),
                    extra_tags="Cannot delete department",
                )

            return redirect("admin_departments")

        else:
            raise Http404

    # Search Departments
    q = request.GET.get("q", "").strip()

    departments = Department.objects.annotate(
        recipient_count=Count("recipient")
    )

    if q:
        departments = departments.filter(
            department_name__icontains=q
        )

    return render(
        request,
        "administration/departments.html",
        {
            "departments": departments.order_by("department_name"),
            "q": q,
            "add_form": add_form,
            "rename_form": rename_form,
            "rename_id": rename_id,
            "open_modal": open_modal,
        },
    )
