from django.shortcuts import render

# Create your views here.
from django.contrib.auth import views as auth_views

from .forms import EmailAuthenticationForm


class LoginView(auth_views.LoginView):
    template_name = "accounts/login.html"
    authentication_form = EmailAuthenticationForm
    redirect_authenticated_user = True
