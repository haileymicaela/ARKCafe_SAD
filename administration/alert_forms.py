from django import forms
from django.core.validators import RegexValidator

from core.models import Recipient


class AlertRecipientForm(forms.ModelForm):
    mobile_number = forms.CharField(
        max_length=20,
        validators=[RegexValidator(r"^\d{11}$", "Enter an 11-digit mobile number.")],
        widget=forms.TextInput(
            attrs={"placeholder": "09XXXXXXXXX", "inputmode": "numeric", "maxlength": "11"}
        ),
    )

    class Meta:
        model = Recipient
        fields = ["name", "mobile_number", "department"]
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "Enter recipient name"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["department"].empty_label = "Select department"
        # Required messages
        self.fields["name"].error_messages["required"] = "Name is required."
        self.fields["mobile_number"].error_messages["required"] = "Mobile number is required."
        self.fields["department"].error_messages["required"] = "Please select a department."
