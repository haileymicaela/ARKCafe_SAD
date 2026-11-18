from django.contrib.auth.views import LoginView
from django.shortcuts import resolve_url

from .forms import EmailLoginForm


class CrimsonLoginView(LoginView):
    template_name = "accounts/login.html"
    authentication_form = EmailLoginForm
    redirect_authenticated_user = True

    def get_success_url(self):
        # Honour a safe ?next= first, otherwise land on the role's dashboard.
        redirect_to = self.get_redirect_url()
        if redirect_to:
            return redirect_to
        user = self.request.user
        return resolve_url("admin_dashboard" if user.role == user.ADMIN else "staff_dashboard")
