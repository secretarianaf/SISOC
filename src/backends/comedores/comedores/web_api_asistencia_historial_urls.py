"""Rutas de ``/api/web/comedores/comedores/`` (G1 v1) del historial de asistencia: ver ``comedores.web_api_asistencia_historial``."""

from django.urls import path

from comedores.web_api_asistencia_historial import NominaAsistenciaHistorialWebView

urlpatterns = [
    path(
        "comedores/<int:pk>/admision/<int:admision_pk>/nomina/asistencia/",
        NominaAsistenciaHistorialWebView.as_view(),
        name="comedores_web_nomina_asistencia_historial",
    ),
]
