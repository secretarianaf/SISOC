"""Session web API for bulk-credentials jobs, under ``/api/web/users/bulk-credentials/``."""

from django.urls import path

from usuarios.web_bulk_credentials import (
    WebBulkCredentialsJobResumeView,
    WebBulkCredentialsJobView,
    WebBulkCredentialsView,
)

urlpatterns = [
    path("", WebBulkCredentialsView.as_view(), name="web_bulk_credentials"),
    path(
        "jobs/<int:pk>/",
        WebBulkCredentialsJobView.as_view(),
        name="web_bulk_credentials_job",
    ),
    path(
        "jobs/<int:pk>/resume/",
        WebBulkCredentialsJobResumeView.as_view(),
        name="web_bulk_credentials_job_resume",
    ),
]
