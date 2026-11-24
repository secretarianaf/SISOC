"""Rutas de ``/api/web/comedores/comedores/`` (G1 v1) del historial de certificaciones: ver ``comedores.web_api_certificaciones``."""

from django.urls import path

from comedores.web_api_certificaciones import CertificacionesHistorialWebView

urlpatterns = [
    path(
        "comedores/<int:pk>/certificaciones-prestaciones/",
        CertificacionesHistorialWebView.as_view(),
        name="comedores_web_certificaciones_historial",
    ),
]
