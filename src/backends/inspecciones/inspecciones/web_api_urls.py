"""Rutas de ``/api/web/inspecciones/`` (G1 v1): ver ``inspecciones.web_api``."""

from django.urls import path

from inspecciones.web_api import ActasWebView, InspectoresWebView
from inspecciones.web_api_acta import (
    ActaDetalleWebView,
    AnularActaWebView,
    MarcarPruebaWebView,
)

urlpatterns = [
    path("actas/", ActasWebView.as_view(), name="inspecciones_web_actas"),
    path(
        "actas/<str:numero>/",
        ActaDetalleWebView.as_view(),
        name="inspecciones_web_acta_detalle",
    ),
    path(
        "actas/<str:numero>/anular/",
        AnularActaWebView.as_view(),
        name="inspecciones_web_acta_anular",
    ),
    path(
        "actas/<str:numero>/prueba/",
        MarcarPruebaWebView.as_view(),
        name="inspecciones_web_acta_prueba",
    ),
    path(
        "inspectores/",
        InspectoresWebView.as_view(),
        name="inspecciones_web_inspectores",
    ),
]
