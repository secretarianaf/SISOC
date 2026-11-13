"""Rutas de ``/api/web/cdi/`` de los trabajadores del centro (CDI05, G1 v1).

Ver ``centrodeinfancia.web_api_trabajador_detalle`` (ficha de un trabajador) y
``centrodeinfancia.web_api_trabajador_form`` (alta y edición).
"""

from django.urls import path

from centrodeinfancia.web_api_trabajador_detalle import TrabajadorDetalleWebView
from centrodeinfancia.web_api_trabajador_form import (
    TrabajadorCrearWebView,
    TrabajadorEditarWebView,
)

urlpatterns = [
    path(
        "centros/<int:pk>/trabajadores/<int:trabajador_id>/",
        TrabajadorDetalleWebView.as_view(),
        name="centrodeinfancia_web_trabajador_detalle",
    ),
    path(
        "centros/<int:pk>/trabajadores/crear/",
        TrabajadorCrearWebView.as_view(),
        name="centrodeinfancia_web_trabajador_crear",
    ),
    path(
        "centros/<int:pk>/trabajadores/<int:trabajador_id>/editar/",
        TrabajadorEditarWebView.as_view(),
        name="centrodeinfancia_web_trabajador_editar",
    ),
]
