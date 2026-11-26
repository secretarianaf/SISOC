"""Session web API for user-import jobs, mounted under ``/api/web/users/import/``."""

from django.urls import path

from usuarios.web_user_import import (
    WebUserImportJobResumeView,
    WebUserImportJobView,
    WebUserImportView,
)

urlpatterns = [
    path("", WebUserImportView.as_view(), name="web_user_import"),
    path(
        "jobs/<int:pk>/",
        WebUserImportJobView.as_view(),
        name="web_user_import_job",
    ),
    path(
        "jobs/<int:pk>/resume/",
        WebUserImportJobResumeView.as_view(),
        name="web_user_import_job_resume",
    ),
]
