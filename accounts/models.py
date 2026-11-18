from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.db import models


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra):
        if not email:
            raise ValueError("Email is required")
        user = self.model(email=self.normalize_email(email), **extra)
        user.set_password(password)  # stored in password_hash
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra):
        extra.setdefault("role", "admin")
        return self.create_user(email, password, **extra)


class User(AbstractBaseUser):
    ROLES = [("admin", "Admin"), ("staff", "Staff")]

    user_id = models.AutoField(primary_key=True)
    full_name = models.CharField(max_length=100)
    email = models.EmailField(max_length=255, unique=True)
    password = models.CharField(max_length=255, db_column="password_hash")
    department_id = models.IntegerField(null=True, blank=True)  # FK later
    role = models.CharField(max_length=20, choices=ROLES, default="staff")
    is_active = models.BooleanField(default=True)

    last_login = None  # table has no last_login column

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["full_name"]
    objects = UserManager()

    class Meta:
        db_table = "user_account"

    # keep the rest of the app (home view, Django admin) working
    @property
    def is_superuser(self):
        return self.role == "admin"

    @property
    def is_staff(self):
        return self.role == "admin"

    def has_perm(self, perm, obj=None):
        return self.is_active and self.is_superuser

    def has_module_perms(self, app_label):
        return self.is_active and self.is_superuser