from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.db.models.functions import Lower
from django.db.models.deletion import ProtectedError
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render

from accounts.models import User
from core.decorators import admin_required

from .user_forms import AdminPasswordResetForm, UserCreateForm, UserEditForm

PAGE_SIZE = 8
USER_ACTIONS = {"edit", "reset", "deactivate", "delete"}


def _target(request):
    try:
        pk = int(request.POST.get("user_id", ""))
    except ValueError:
        raise Http404
    return get_object_or_404(User, pk=pk)


def _has_records(user):
    return (
        user.ncrs_created.exists()
        or user.audit_entries.exists()
        or user.activities.exists()
    )


@admin_required
def admin_users(request):
    add_form = UserCreateForm(prefix="add")
    edit_form = UserEditForm(prefix="edit")
    reset_form = AdminPasswordResetForm(prefix="reset")
    open_modal = ""
    edit_id = ""
    edit_was_active = ""
    reset_target = None

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "add":
            add_form = UserCreateForm(request.POST, prefix="add")
            if add_form.is_valid():
                user = add_form.save()
                messages.success(request, f"Account Created for {user.full_name}")
                return redirect("admin_users")
            open_modal = "add"

        elif action in USER_ACTIONS:
            target = _target(request)
            is_self = target.pk == request.user.pk

            if action == "edit":
                edit_was_active = "1" if target.is_active else "0"
                edit_form = UserEditForm(
                    request.POST, instance=target, prefix="edit", acting_user=request.user
                )
                if edit_form.is_valid():
                    edit_form.save()
                    messages.success(request, f"Changes saved for {target.full_name}")
                    return redirect("admin_users")
                open_modal = "edit"
                edit_id = target.pk

            elif action == "reset":
                reset_form = AdminPasswordResetForm(request.POST, prefix="reset")
                if reset_form.is_valid():
                    target.set_password(reset_form.cleaned_data["new_password1"])
                    target.save()
                    if is_self:
                        update_session_auth_hash(request, target)
                    messages.success(request, f"Password reset for {target.full_name}")
                    return redirect("admin_users")
                open_modal = "reset"
                reset_target = target

            elif action == "deactivate":
                if is_self:
                    messages.error(request, "You can't deactivate your own account.")
                else:
                    target.is_active = False
                    target.save()
                    messages.success(request, f"{target.full_name} was deactivated")
                return redirect("admin_users")

            elif action == "delete":
                if is_self:
                    messages.error(request, "You can't delete your own account.")
                elif _has_records(target):
                    messages.error(
                        request,
                        f"{target.full_name} has records and can't be deleted. Deactivate instead.",
                    )
                else:
                    name = target.full_name
                    try:
                        target.delete()
                        messages.success(request, f"Account deleted for {name}")
                    except ProtectedError:
                        messages.error(
                            request,
                            f"{name} has records and can't be deleted. Deactivate instead.",
                        )
                return redirect("admin_users")
        else:
            raise Http404

    # ---- list, search, filter, sort, paginate ----
    q = request.GET.get("q", "").strip()
    role = request.GET.get("role", "")
    status = request.GET.get("status", "")
    sort = request.GET.get("sort", "name_asc")

    users = User.objects.select_related("department").annotate(
        ncr_count=Count("ncrs_created", distinct=True),
        audit_count=Count("audit_entries", distinct=True),
        activity_count=Count("activities", distinct=True),
    )
    if q:
        users = users.filter(Q(full_name__icontains=q) | Q(email__icontains=q))
    if role in (User.ADMIN, User.STAFF):
        users = users.filter(role=role)
    if status == "active":
        users = users.filter(is_active=True)
    elif status == "inactive":
        users = users.filter(is_active=False)
    users = users.order_by(Lower("full_name").desc() if sort == "name_desc" else Lower("full_name"))

    page_obj = Paginator(users, PAGE_SIZE).get_page(request.GET.get("page"))

    params = request.GET.copy()
    params.pop("page", None)

    return render(
        request,
        "administration/users.html",
        {
            "page_obj": page_obj,
            "q": q,
            "role": role,
            "status": status,
            "sort": sort,
            "roles": User.ROLES,
            "qs": params.urlencode(),
            "add_form": add_form,
            "edit_form": edit_form,
            "reset_form": reset_form,
            "open_modal": open_modal,
            "edit_id": edit_id,
            "edit_was_active": edit_was_active,
            "reset_target": reset_target,
        },
    )