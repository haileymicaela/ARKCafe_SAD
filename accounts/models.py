from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.db import models


class UserManager(BaseUserManager):
    use_in_migrations = True

    def get_by_natural_key(self, email):
        # Emails are stored lowercased, but match case-insensitively on login.
        return self.get(email__iexact=email)

    def _create_user(self, email, full_name, password, **extra_fields):
        if not email:
            raise ValueError("An email address is required.")
        user = self.model(
            email=self.normalize_email(email).lower(),
            full_name=full_name,
            **extra_fields,
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, full_name="", password=None, **extra_fields):
        extra_fields.setdefault("role", User.STAFF)
        return self._create_user(email, full_name, password, **extra_fields)

    def create_superuser(self, email, full_name="", password=None, **extra_fields):
        extra_fields["role"] = User.ADMIN
        return self._create_user(email, full_name, password, **extra_fields)


class User(AbstractBaseUser):
    """Maps to the `user_account` table.

    department_id is intentionally omitted for now; it will be added as a
    ForeignKey once the Department model exists.
    """

    ADMIN = "admin"
    STAFF = "staff"
    ROLES = [(ADMIN, "Admin"), (STAFF, "Staff")]

    user_id = models.AutoField(primary_key=True)
    full_name = models.CharField(max_length=100)
    email = models.EmailField(max_length=255, unique=True)
    # Django's `password` attribute, stored in the table's password_hash column.
    password = models.CharField("password", max_length=255, db_column="password_hash")
    role = models.CharField(max_length=20, choices=ROLES, default=STAFF)
    is_active = models.BooleanField(default=True)

    # The table has no last_login column.
    last_login = None

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["full_name"]

    class Meta:
        db_table = "user_account"

    def __str__(self):
        return self.email

    def save(self, *args, **kwargs):
        self.email = self.email.strip().lower()
        super().save(*args, **kwargs)

    def get_full_name(self):
        return self.full_name

    def get_short_name(self):
        return self.full_name.split(" ")[0] if self.full_name else self.email

    @property
    def is_admin_role(self):
        return self.role == self.ADMIN

    # --- Django admin site support (no groups/permissions tables) ---
    @property
    def is_staff(self):
        return self.is_active and self.role == self.ADMIN

    @property
    def is_superuser(self):
        return self.is_active and self.role == self.ADMIN

    def has_perm(self, perm, obj=None):
        return self.is_superuser

    def has_module_perms(self, app_label):
        return self.is_superuser
