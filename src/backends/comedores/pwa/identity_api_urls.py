"""Recupero de Espacios en su dueño; el portal conserva la URL pública."""

from django.urls import path
from pwa.identity_services import EspaciosPasswordResetView

urlpatterns = [path("password-reset/request/", EspaciosPasswordResetView.as_view())]
