"""Rutas de ``/api/web/comedores/admisiones/informes/`` (G1 v1).

Ver ``admisiones.web_api_informes``.
"""

from django.urls import path

from admisiones.web_api_informes import InformeDetailWebView

urlpatterns = [
    path(
        "<str:tipo>/<int:pk>/",
        InformeDetailWebView.as_view(),
        name="informe_tecnico_web_detalle",
    ),
]
