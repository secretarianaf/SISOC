"""Rutas de ``/api/web/comedores/relevamientos/`` (G1 v1): ver ``relevamientos.web_api_views``."""

from django.urls import path

from relevamientos.web_api_views import (
    RelevamientoDetalleWebView,
    RelevamientosListadoWebView,
)

urlpatterns = [
    path(
        "<int:comedor_pk>/",
        RelevamientosListadoWebView.as_view(),
        name="relevamientos_web_listado",
    ),
    path(
        "<int:comedor_pk>/relevamiento/<int:pk>/",
        RelevamientoDetalleWebView.as_view(),
        name="relevamientos_web_detalle",
    ),
]
