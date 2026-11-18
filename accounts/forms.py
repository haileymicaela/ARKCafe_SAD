
from django import forms
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.forms import AuthenticationForm


class EmailAuthenticationForm(AuthenticationForm):
    username = forms.EmailField(
        label="Email",
        widget=forms.EmailInput(attrs={
            "placeholder": "Email",
            "autocomplete": "email",
            "autofocus": True,
        }),
    )

    password = forms.CharField(
        label="Password",
        strip=False,
        widget=forms.PasswordInput(attrs={
            "placeholder": "Password",
            "autocomplete": "current-password",
        }),
    )

    error_messages = {
        "invalid_login": "Incorrect email or password. Check both and try again.",
        "inactive": "This account is deactivated. Contact an administrator.",
    }

    def clean(self):
        email = self.cleaned_data.get("username")
        password = self.cleaned_data.get("password")

        if email and password:
            User = get_user_model()
            user = User._default_manager.filter(email__iexact=email).first()
            identifier = getattr(user, User.USERNAME_FIELD) if user else email

            self.user_cache = authenticate(
                self.request,
                username=identifier,
                password=password
            )

            if self.user_cache is None:
                raise self.get_invalid_login_error()

            self.confirm_login_allowed(self.user_cache)

        return self.cleaned_data
