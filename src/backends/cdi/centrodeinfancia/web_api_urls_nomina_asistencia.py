"""Rutas de ``/api/web/cdi/`` de la asistencia de la nómina (G1 v1).

Ver ``centrodeinfancia.web_api_nomina_asistencia``. El calendario mensual sigue siendo el
endpoint JSON nativo.
"""

from django.urls import path

from centrodeinfancia.web_api_nomina_asistencia import AsistenciaWebView

urlpatterns = [
    path(
        "centros/<int:pk>/nomina/asistencia/",
        AsistenciaWebView.as_view(),
        name="centrodeinfancia_web_nomina_asistencia",
    ),
]
