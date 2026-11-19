import os

from django import forms
from django.utils import timezone

from core.models import Department, NcrRecord, Project

from .services import allowed_next

MAX_FILES = 5
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB
ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".doc", ".docx", ".xls", ".xlsx"}


class BootstrapMixin:
    def _style(self):
        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, forms.Select):
                widget.attrs["class"] = "form-select"
            else:
                widget.attrs["class"] = "form-control"


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True
    
    # Idinagdag natin ito para laging naka-set ang 'multiple' attribute
    def __init__(self, attrs=None):
        super().__init__(attrs)
        self.attrs['multiple'] = True


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
        help_text="Up to 5 files, 5 MB each (PDF, images, Word, Excel).",
    )

    class Meta:
        model = NcrRecord
        fields = [
            "project", "department", "package_no", "cause", "subject",
            "issued_date", "required_date", "description",
        ]
        labels = {
            "package_no": "Package No.",
            "issued_date": "Issued Date",
            "required_date": "Required Date",
            "cause": "Cause",
        }
        widgets = {
            "issued_date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "required_date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "description": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["project"].queryset = Project.objects.order_by("project_name")
        self.fields["department"].queryset = Department.objects.order_by("department_name")
        if not self.instance.pk:
            self.fields["issued_date"].initial = timezone.localdate()
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
    new_status = forms.ChoiceField(label="New status")
    resolution_type = forms.ChoiceField(
        required=False,
        label="Resolution",
        choices=[("", "Select resolution")] + NcrRecord.RESOLUTION_CHOICES,
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
        self._style()

    def clean(self):
        data = super().clean()
        if data.get("new_status") == NcrRecord.STATUS_RESOLVED and not data.get("resolution_type"):
            self.add_error("resolution_type", "Choose how this NCR was resolved.")
        return data