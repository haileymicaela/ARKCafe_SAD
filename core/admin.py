from django.contrib import admin

from .models import (
    ActivityLog,
    Attachment,
    AuditLog,
    Department,
    NcrRecord,
    Project,
    Recipient,
)

admin.site.register(Department)
admin.site.register(Project)
admin.site.register(Recipient)
admin.site.register(NcrRecord)
admin.site.register(Attachment)
admin.site.register(AuditLog)
admin.site.register(ActivityLog)