"""Rutas de ``/api/web/comedores/comunicados/mailing/`` (G1 v1): ver ``comunicados.web_api_mailing``."""

from django.urls import path

from comunicados.web_api_mailing import (
    MailingFormWebView,
    MailingJobWebView,
    MailingResumeWebView,
)

urlpatterns = [
    path("", MailingFormWebView.as_view(), name="comunicados_web_mailing"),
    path(
        "jobs/<int:pk>/",
        MailingJobWebView.as_view(),
        name="comunicados_web_mailing_job",
    ),
    path(
        "jobs/<int:pk>/resume/",
        MailingResumeWebView.as_view(),
        name="comunicados_web_mailing_resume",
    ),
]
