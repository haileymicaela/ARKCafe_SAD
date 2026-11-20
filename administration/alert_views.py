from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .alert_forms import AlertRecipientForm
from .models import AlertRecipient

# Match the template folder you used for projects.html
TEMPLATE = "administration/alert_recipients.html"

# NOTE: Alert Recipients is accessible by BOTH roles, so only login is required.
# Add your own role check here if you have a decorator for allowed roles.


def _render(request, form=None, modal_title=None, modal_action=None, status=200):
    q = request.GET.get("q", "").strip()
    qs = AlertRecipient.objects.select_related("department")
    if q:
        qs = qs.filter(name__icontains=q)

    ctx = {
        "recipients": qs,
        "q": q,
        "total": qs.count(),
        "form": form or AlertRecipientForm(),
        "modal_title": modal_title,
        "modal_action": modal_action,
        # one-time success popup (set by add / edit / delete)
        "success": request.session.pop("alert_success", None),
    }
    return render(request, TEMPLATE, ctx, status=status)


def _flash(request, title, text):
    request.session["alert_success"] = {"title": title, "text": text}


@login_required
def recipient_list(request):
    return _render(request)


@login_required
def recipient_add(request):
    if request.method != "POST":
        return redirect("alert_recipients")

    form = AlertRecipientForm(request.POST)
    if form.is_valid():
        obj = form.save()
        _flash(request, "Recipient added", f"{obj.name} was added successfully")
        return redirect("alert_recipients")

    return _render(request, form=form, modal_title="Add Recipient",
                   modal_action=request.path)


@login_required
def recipient_edit(request, pk):
    obj = get_object_or_404(AlertRecipient, pk=pk)
    if request.method != "POST":
        return redirect("alert_recipients")

    form = AlertRecipientForm(request.POST, instance=obj)
    if form.is_valid():
        form.save()
        _flash(request, "Recipient edited", "Your edit was saved successfully")
        return redirect("alert_recipients")

    return _render(request, form=form, modal_title="Edit Recipient Information",
                   modal_action=request.path)


@login_required
@require_POST
def recipient_delete(request, pk):
    obj = get_object_or_404(AlertRecipient, pk=pk)
    name = obj.name
    obj.delete()
    _flash(request, "Recipient removed", f"{name} was removed successfully")
    return redirect("alert_recipients")