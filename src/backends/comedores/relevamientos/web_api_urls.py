"""Rutas de ``/api/web/comedores/relevamientos/`` (G1 v1): ver ``relevamientos.web_api_views``."""

from django.urls import path

from relevamientos.web_api_views import (
    ActaDetalleWebView,
    SeguimientoDetalleWebView,
    SeguimientoPnudDetalleWebView,
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
    path(
        "<int:comedor_pk>/relevamiento/<int:relevamiento_pk>/seguimientos/primero/",
        SeguimientoDetalleWebView.as_view(),
        name="relevamientos_web_seguimiento_primero",
    ),
    path(
        "<int:comedor_pk>/relevamiento/<int:relevamiento_pk>/seguimientos/<int:pk>/",
        SeguimientoDetalleWebView.as_view(),
        name="relevamientos_web_seguimiento",
    ),
    path(
        "<int:comedor_pk>/pnud/<int:pk>/",
        SeguimientoPnudDetalleWebView.as_view(),
        name="relevamientos_web_pnud",
    ),
    path(
        "<int:comedor_pk>/actas/<int:pk>/",
        ActaDetalleWebView.as_view(),
        name="relevamientos_web_acta",
    ),
]
