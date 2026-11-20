from django.db import models
from django.core.validators import RegexValidator
from core.models import Department

class AlertRecipient(models.Model):
    name = models.CharField(max_length=150)
    mobile_number = models.CharField(
        max_length=11,
        validators=[RegexValidator(r"^\d{11}$", "Enter an 11-digit mobile number.")],
    )
    department = models.ForeignKey(
        Department, on_delete=models.PROTECT, related_name="alert_recipients"
    )

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return self.name