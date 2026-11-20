from django.urls import path

from . import views

# staff_records and staff_create_ncr keep the same names/paths the sidebar already uses.
urlpatterns = [
    path("staff-records/", views.staff_records, name="staff_records"),
    path("staff-create/", views.staff_create_ncr, name="staff_create_ncr"),
    path("staff-records/<int:pk>/", views.ncr_detail, name="ncr_detail"),
    path("staff-records/<int:pk>/edit/", views.ncr_edit, name="ncr_edit"),
    path("staff-records/<int:pk>/attachments/<int:attachment_id>/", views.ncr_attachment, name="ncr_attachment"),
    path("staff-records/<int:pk>/attachments/<int:attachment_id>/delete/", views.ncr_attachment_delete, name="ncr_attachment_delete"),
]