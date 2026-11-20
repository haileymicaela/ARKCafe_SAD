from django import forms

from accounts.models import User
from core.models import Department


class _Styled:
    def _style_fields(self):
        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, forms.RadioSelect):
                continue
            css = "form-select" if isinstance(widget, forms.Select) else "form-control"
            widget.attrs["class"] = css


def _email_taken(email, exclude_pk=None):
    qs = User.objects.filter(email__iexact=email)
    if exclude_pk:
        qs = qs.exclude(pk=exclude_pk)
    return qs.exists()


def _role_choices():
    return [("", "Select Role")] + list(User.ROLES)


class UserCreateForm(_Styled, forms.ModelForm):
    role = forms.ChoiceField(choices=_role_choices)
    password1 = forms.CharField(
        label="Temporary Password",
        min_length=8,
        widget=forms.PasswordInput(
            attrs={"placeholder": "At least 8 characters", "autocomplete": "new-password"}
        ),
    )
    password2 = forms.CharField(
        label="Confirm Password",
        widget=forms.PasswordInput(
            attrs={"placeholder": "Re-enter the password", "autocomplete": "new-password"}
        ),
    )

    class Meta:
        model = User
        fields = ["full_name", "email", "department", "role"]
        labels = {"full_name": "Full Name", "email": "Email"}
        widgets = {
            "full_name": forms.TextInput(attrs={"placeholder": "Enter Full name"}),
            "email": forms.EmailInput(attrs={"placeholder": "name@company.com"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        dept = self.fields["department"]
        dept.required = True
        dept.empty_label = "Select Department"
        dept.queryset = Department.objects.order_by("department_name")
        self._style_fields()

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if _email_taken(email, self.instance.pk):
            raise forms.ValidationError("An account with this email already exists.")
        return email

    def clean(self):
        data = super().clean()
        p1, p2 = data.get("password1"), data.get("password2")
        if p1 and p2 and p1 != p2:
            self.add_error("password2", "The passwords do not match.")
        return data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user


class UserEditForm(_Styled, forms.ModelForm):
    role = forms.ChoiceField(choices=_role_choices)
    is_active = forms.TypedChoiceField(
        choices=[("1", "Active"), ("0", "Inactive")],
        coerce=lambda v: v == "1",
        initial="1",
        widget=forms.RadioSelect,
    )

    class Meta:
        model = User
        fields = ["full_name", "email", "department", "role", "is_active"]
        labels = {"full_name": "Full Name", "email": "Email"}

    def __init__(self, *args, acting_user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.acting_user = acting_user
        dept = self.fields["department"]
        dept.required = True
        dept.empty_label = "Select Department"
        dept.queryset = Department.objects.order_by("department_name")
        self._style_fields()

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if _email_taken(email, self.instance.pk):
            raise forms.ValidationError("An account with this email already exists.")
        return email

    def clean(self):
        data = super().clean()
        is_self = (
            self.acting_user is not None
            and self.instance.pk is not None
            and self.instance.pk == self.acting_user.pk
        )
        if is_self:
            if data.get("is_active") is False:
                self.add_error("is_active", "You can't deactivate your own account.")
            if data.get("role") and data["role"] != User.ADMIN:
                self.add_error("role", "You can't remove your own admin role.")
        return data


class AdminPasswordResetForm(_Styled, forms.Form):
    new_password1 = forms.CharField(
        label="New Temporary Password",
        min_length=8,
        widget=forms.PasswordInput(
            attrs={"placeholder": "At least 8 characters", "autocomplete": "new-password"}
        ),
    )
    new_password2 = forms.CharField(
        label="Confirm Password",
        widget=forms.PasswordInput(
            attrs={"placeholder": "Re-enter the password", "autocomplete": "new-password"}
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._style_fields()

    def clean(self):
        data = super().clean()
        p1, p2 = data.get("new_password1"), data.get("new_password2")
        if p1 and p2 and p1 != p2:
            self.add_error("new_password2", "The passwords do not match.")
        return data