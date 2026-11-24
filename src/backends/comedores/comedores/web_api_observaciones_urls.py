"""Rutas de ``/api/web/comedores/observaciones/`` (G1 v1): ver ``comedores.web_api_observaciones``."""

from django.urls import path

from comedores.web_api_observaciones import (
    ObservacionBajaWebView,
    ObservacionCrearWebView,
    ObservacionDetalleWebView,
    ObservacionEditarWebView,
)

urlpatterns = [
    path(
        "comedor/<comedor_pk>/crear/",
        ObservacionCrearWebView.as_view(),
        name="observaciones_web_crear",
    ),
    path(
        "<int:pk>/",
        ObservacionDetalleWebView.as_view(),
        name="observaciones_web_detalle",
    ),
    path(
        "<int:pk>/editar/",
        ObservacionEditarWebView.as_view(),
        name="observaciones_web_editar",
    ),
    path(
        "<int:pk>/eliminar/",
        ObservacionBajaWebView.as_view(),
        name="observaciones_web_eliminar",
    ),
]
