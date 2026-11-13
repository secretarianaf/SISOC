"""Rutas de ``/api/web/cdi/`` de los trabajadores del centro (CDI05, G1 v1).

Ver ``centrodeinfancia.web_api_trabajador_detalle`` (ficha de un trabajador).
"""

from django.urls import path

from centrodeinfancia.web_api_trabajador_detalle import TrabajadorDetalleWebView

urlpatterns = [
    path(
        "centros/<int:pk>/trabajadores/<int:trabajador_id>/",
        TrabajadorDetalleWebView.as_view(),
        name="centrodeinfancia_web_trabajador_detalle",
    ),
]
