import os

from django import forms
from django.utils import timezone

from core.models import Department, NcrRecord, Project

from .services import allowed_next

MAX_FILES = 15
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB
ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".doc", ".docx", ".xls", ".xlsx"}


class BootstrapMixin:
    def _style(self):
        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, forms.RadioSelect):
                continue
            elif isinstance(widget, forms.Select):
                widget.attrs["class"] = "form-select"
            else:
                widget.attrs["class"] = "form-control"


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_clean = super().clean
        if isinstance(data, (list, tuple)):
            return [single_clean(d, initial) for d in data]
        return [single_clean(data, initial)] if data else []


class NcrForm(BootstrapMixin, forms.ModelForm):
    attachments = MultipleFileField(
        required=False,
        help_text="Up to 15 files, 5 MB each (PDF, images, Word, Excel).",
    )

    class Meta:
        model = NcrRecord
        fields = [
            "project", "department", "package_no", "cause", "subject",
            "issued_date", "required_date", "description",
        ]
        labels = {
            "package_no": "Package No.",
            "issued_date": "Date raised",
            "required_date": "Required Date",
            "cause": "Cause",
            "department": "Responsible department",
            "description": "Description of non-conformance",
        }
        widgets = {
            "package_no": forms.TextInput(attrs={"placeholder": "e.g. PKG-114"}),
            "subject": forms.TextInput(attrs={"placeholder": "Short summary of the non-conformance"}),
            "issued_date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "required_date": forms.DateInput(attrs={"type": "date", "placeholder": "Select date"}, format="%Y-%m-%d"),
            "description": forms.Textarea(attrs={
                "rows": 4,
                "placeholder": "Describe what was found, where, and which approved specification it deviates from...",
            }),
            "cause": forms.RadioSelect,
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["project"].queryset = Project.objects.order_by("project_name")
        self.fields["department"].queryset = Department.objects.order_by("department_name")
        self.fields["project"].empty_label = "Select a project"
        self.fields["department"].empty_label = "Select department"
        if not self.instance.pk:
            self.fields["issued_date"].initial = timezone.localdate()
            self.fields["cause"].initial = NcrRecord.CAUSE_CHOICES[0][0]
        self.fields["issued_date"].disabled = True
        self._style()

    def clean_attachments(self):
        files = self.cleaned_data.get("attachments") or []
        if len(files) > MAX_FILES:
            raise forms.ValidationError(f"You can upload at most {MAX_FILES} files at a time.")
        for f in files:
            ext = os.path.splitext(f.name)[1].lower()
            if ext not in ALLOWED_EXTENSIONS:
                raise forms.ValidationError(
                    f'"{f.name}" is not an allowed file type (PDF, images, Word, Excel only).'
                )
            if f.size > MAX_FILE_SIZE:
                raise forms.ValidationError(f'"{f.name}" is larger than 5 MB.')
        return files

    def clean(self):
        data = super().clean()
        issued, required = data.get("issued_date"), data.get("required_date")
        if issued and required and required < issued:
            self.add_error("required_date", "Required date cannot be earlier than the issued date.")
        return data


class StatusUpdateForm(BootstrapMixin, forms.Form):
    new_status = forms.ChoiceField(label="New status", widget=forms.RadioSelect)
    resolve_date = forms.DateField(
        required=False,
        label="Resolution date",
        widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
    )
    resolution_type = forms.ChoiceField(
        required=False,
        label="Resolution",
        choices=[("", "Select resolution")] + NcrRecord.RESOLUTION_CHOICES,
        widget=forms.RadioSelect,
    )
    resolution_note = forms.CharField(
        required=False, label="Resolution note", widget=forms.Textarea(attrs={"rows": 2})
    )
    remarks = forms.CharField(
        required=False, label="Remarks", widget=forms.Textarea(attrs={"rows": 2})
    )

    def __init__(self, *args, ncr, **kwargs):
        super().__init__(*args, **kwargs)
        labels = dict(NcrRecord.STATUS_CHOICES)
        self.fields["new_status"].choices = [(s, labels[s]) for s in allowed_next(ncr.status)]
        self.fields["resolve_date"].initial = timezone.localdate()
        self._style()

    def clean(self):
        data = super().clean()
        if data.get("new_status") == NcrRecord.STATUS_RESOLVED and not data.get("resolution_type"):
            self.add_error("resolution_type", "Choose how this NCR was resolved.")
        if data.get("new_status") == NcrRecord.STATUS_RESOLVED and not data.get("resolve_date"):
            data["resolve_date"] = timezone.localdate()
        return data
