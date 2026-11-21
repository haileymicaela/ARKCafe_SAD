from django.conf import settings
from django.db import models


class Department(models.Model):
    department_id = models.AutoField(primary_key=True)
    department_name = models.CharField(max_length=100, unique=True)

    class Meta:
        db_table = "department"

    def __str__(self):
        return self.department_name


class Project(models.Model):
    project_id = models.AutoField(primary_key=True)
    project_name = models.CharField(max_length=150)
    client_name = models.CharField(max_length=150)
    project_code = models.CharField(max_length=30, unique=True)
    description = models.TextField(blank=True)

    class Meta:
        db_table = "projects"

    def __str__(self):
        return f"{self.project_code} - {self.project_name}"


class Recipient(models.Model):
    recipient_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=150)
    mobile_number = models.CharField(max_length=20)
    department = models.ForeignKey(
        Department, on_delete=models.PROTECT, db_column="department_id"
    )

    class Meta:
        db_table = "recipients"

    def __str__(self):
        return self.name


class NcrRecord(models.Model):
    # Cause tags (system request: material, workmanship, sequencing)
    CAUSE_MATERIAL = "material"
    CAUSE_WORKMANSHIP = "workmanship"
    CAUSE_SEQUENCING = "sequencing"
    CAUSE_CHOICES = [
        (CAUSE_MATERIAL, "Material"),
        (CAUSE_WORKMANSHIP, "Workmanship"),
        (CAUSE_SEQUENCING, "Sequencing"),
    ]

    # Lifecycle: open -> in progress -> resolved (a resolved NCR can be reopened)
    STATUS_OPEN = "open"
    STATUS_IN_PROGRESS = "in_progress"
    STATUS_RESOLVED = "resolved"
    STATUS_CHOICES = [
        (STATUS_OPEN, "Open"),
        (STATUS_IN_PROGRESS, "In Progress"),
        (STATUS_RESOLVED, "Resolved"),
    ]

    # How a resolved NCR was resolved
    RESOLUTION_CHOICES = [
        ("replaced", "Replaced"),
        ("reapproved", "Reapproved"),
        ("closed", "Closed"),
    ]

    # Dashboard grouping: "open" = open + in progress, "closed" = everything resolved
    OPEN_STATUSES = [STATUS_OPEN, STATUS_IN_PROGRESS]
    CLOSED_STATUSES = [STATUS_RESOLVED]

    ncr_id = models.AutoField(primary_key=True)
    project = models.ForeignKey(
        Project, on_delete=models.PROTECT, db_column="project_id"
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        db_column="created_by",
        related_name="ncrs_created",
    )
    department = models.ForeignKey(
        Department, on_delete=models.PROTECT, db_column="department_id"
    )
    reference_no = models.CharField(max_length=50, unique=True)
    package_no = models.CharField(max_length=50, blank=True)
    subject = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    cause = models.TextField(choices=CAUSE_CHOICES)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default=STATUS_OPEN)
    resolution_type = models.CharField(max_length=50, choices=RESOLUTION_CHOICES, blank=True)
    resolution_note = models.TextField(blank=True)
    issued_date = models.DateField(null=True, blank=True)
    required_date = models.DateField(null=True, blank=True)
    resolve_date = models.DateField(null=True, blank=True)

    class Meta:
        db_table = "ncr_records"

    def __str__(self):
        return self.reference_no


class Attachment(models.Model):
    attachment_id = models.AutoField(primary_key=True)
    ncr = models.ForeignKey(
        NcrRecord, on_delete=models.CASCADE, db_column="ncr_id", related_name="attachments"
    )
    file_name = models.CharField(max_length=255)
    file_type = models.CharField(max_length=100)
    file_data = models.BinaryField()
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "attachments"

    def __str__(self):
        return self.file_name


class AuditLog(models.Model):
    """Status-change history of an NCR."""

    history_id = models.AutoField(primary_key=True)
    ncr = models.ForeignKey(
        NcrRecord, on_delete=models.PROTECT, db_column="ncr_id", related_name="audit_entries"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        db_column="user_id",
        related_name="audit_entries",
    )
    old_status = models.CharField(max_length=30, choices=NcrRecord.STATUS_CHOICES, blank=True)
    new_status = models.CharField(max_length=30, choices=NcrRecord.STATUS_CHOICES)
    remarks = models.TextField(blank=True)
    changed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "audit_log"

    def __str__(self):
        return f"NCR {self.ncr_id}: {self.old_status} -> {self.new_status}"


class ActivityLog(models.Model):
    """General activity feed. entity_id is a loose reference, not a foreign key."""

    activity_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        db_column="user_id",
        related_name="activities",
    )
    action_type = models.CharField(max_length=30)
    entity_type = models.CharField(max_length=30)
    entity_id = models.IntegerField()
    entity_label = models.CharField(max_length=150, blank=True)
    old_value = models.CharField(max_length=255, blank=True)
    new_value = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "activity_log"

    def __str__(self):
        return f"{self.action_type} {self.entity_type} {self.entity_id}"
