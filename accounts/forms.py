from django import forms
from django.contrib.auth.forms import AuthenticationForm


class EmailLoginForm(AuthenticationForm):
    """Login with email + password (User.USERNAME_FIELD is `email`)."""

    username = forms.EmailField(
        label="Email",
        max_length=255,
        widget=forms.EmailInput(
            attrs={"placeholder": "Email", "autocomplete": "username", "autofocus": True}
        ),
    )
    password = forms.CharField(
        label="Password",
        strip=False,
        widget=forms.PasswordInput(
            attrs={"placeholder": "Password", "autocomplete": "current-password"}
        ),
    )

    error_messages = {
        "invalid_login": "Incorrect email or password.",
        "inactive": "Incorrect email or password.",
    }
