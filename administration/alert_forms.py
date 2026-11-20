from django import forms

from .models import AlertRecipient


class AlertRecipientForm(forms.ModelForm):
    class Meta:
        model = AlertRecipient
        fields = ["name", "mobile_number", "department"]
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "Enter recipient name"}),
            "mobile_number": forms.TextInput(
                attrs={"placeholder": "09XXXXXXXXX", "inputmode": "numeric", "maxlength": "11"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["department"].empty_label = "Select department"
        # Required messages
        self.fields["name"].error_messages["required"] = "Name is required."
        self.fields["mobile_number"].error_messages["required"] = "Mobile number is required."
        self.fields["department"].error_messages["required"] = "Please select a department."