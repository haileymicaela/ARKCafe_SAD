from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    ROLES = [("admin", "Admin"), ("staff", "Staff")]
    role = models.CharField(max_length=10, choices=ROLES, default="staff")