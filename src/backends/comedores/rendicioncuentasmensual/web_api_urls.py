"""Rutas de ``/api/web/comedores/rendicioncuentasmensual/`` (G1 v1): ver ``rendicioncuentasmensual.web_api``."""

from django.urls import path

from rendicioncuentasmensual.web_api import RendicionListadoWebView
from rendicioncuentasmensual.web_api_rendicion_detalle import RendicionDetalleWebView

urlpatterns = [
    path(
        "listado/",
        RendicionListadoWebView.as_view(),
        name="rendicioncuentasmensual_web_listado",
    ),
    path(
        "<int:pk>/",
        RendicionDetalleWebView.as_view(),
        name="rendicioncuentasmensual_web_detalle",
    ),
]
