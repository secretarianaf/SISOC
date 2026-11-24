"""Rutas de ``/api/web/comedores/rendicioncuentasmensual/`` (G1 v1): ver ``rendicioncuentasmensual.web_api``."""

from django.urls import path

from rendicioncuentasmensual.web_api import RendicionListadoWebView
from rendicioncuentasmensual.web_api_rendicion_detalle import RendicionDetalleWebView
from rendicioncuentasmensual.web_api_rendicion_por_comedor import (
    RendicionPorComedorWebView,
)
from rendicioncuentasmensual.web_api_rendicion_auditoria import (
    AuditoriaBusquedaWebView,
    AuditoriaGestionWebView,
)
from rendicioncuentasmensual.web_api_rendicion_form import (
    RendicionBajaWebView,
    RendicionEditarWebView,
    RendicionNuevaWebView,
)

urlpatterns = [
    path(
        "listado/",
        RendicionListadoWebView.as_view(),
        name="rendicioncuentasmensual_web_listado",
    ),
    path(
        "por-comedor/<int:comedor_id>/",
        RendicionPorComedorWebView.as_view(),
        name="rendicioncuentasmensual_web_por_comedor",
    ),
    path(
        "<int:pk>/",
        RendicionDetalleWebView.as_view(),
        name="rendicioncuentasmensual_web_detalle",
    ),
    path(
        "nuevo/<int:comedor_id>/",
        RendicionNuevaWebView.as_view(),
        name="rendicioncuentasmensual_web_nuevo",
    ),
    path(
        "editar/<int:pk>/",
        RendicionEditarWebView.as_view(),
        name="rendicioncuentasmensual_web_editar",
    ),
    path(
        "eliminar/<int:pk>/",
        RendicionBajaWebView.as_view(),
        name="rendicioncuentasmensual_web_eliminar",
    ),
    path(
        "auditoria/",
        AuditoriaBusquedaWebView.as_view(),
        name="rendicioncuentasmensual_web_auditoria_busqueda",
    ),
    path(
        "auditoria/<int:pk>/",
        AuditoriaGestionWebView.as_view(),
        name="rendicioncuentasmensual_web_auditoria_gestion",
    ),
]
