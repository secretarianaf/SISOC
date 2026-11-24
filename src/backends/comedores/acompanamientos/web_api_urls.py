"""Rutas de ``/api/web/comedores/acompanamientos/`` (G1 v1): ver ``acompanamientos.web_api``."""

from django.urls import path

from acompanamientos.web_api import (
    AcompanamientoDetailWebView,
    AcompanamientosListWebView,
    RestaurarHitoWebView,
)

urlpatterns = [
    path("", AcompanamientosListWebView.as_view(), name="acompanamientos_web_list"),
    path(
        "<int:comedor_id>/",
        AcompanamientoDetailWebView.as_view(),
        name="acompanamientos_web_detalle",
    ),
    path(
        "<int:comedor_id>/hitos/restaurar/",
        RestaurarHitoWebView.as_view(),
        name="acompanamientos_web_restaurar_hito",
    ),
]
