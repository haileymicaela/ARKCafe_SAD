from django import forms
from core.models import Project

class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = ["project_name", "client_name", "project_code", "description"]
        widgets = {"description": forms.Textarea(attrs={"rows": 3})}

    def clean_project_code(self):
        code = self.cleaned_data["project_code"].strip().upper()
        qs = Project.objects.filter(project_code__iexact=code)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError(
                "Project code already exists. Please use a unique code.")
        return code