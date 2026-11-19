from django import forms

from core.models import Department


class DepartmentForm(forms.ModelForm):
    class Meta:
        model = Department
        fields = ["department_name"]
        labels = {"department_name": "Department Name"}
        widgets = {
            "department_name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Enter department name"}
            )
        }

    def clean_department_name(self):
        name = " ".join(self.cleaned_data["department_name"].split())
        taken = Department.objects.filter(department_name__iexact=name)
        if self.instance.pk:
            taken = taken.exclude(pk=self.instance.pk)
        if taken.exists():
            raise forms.ValidationError("A department with this name already exists.")
        return name