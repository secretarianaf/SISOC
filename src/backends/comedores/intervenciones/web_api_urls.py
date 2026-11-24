"""Rutas de ``/api/web/comedores/intervenciones/`` (G1 v1): ver ``intervenciones.web_api``."""

from django.urls import path

from intervenciones.web_api_formulario import (
    IntervencionCrearWebView,
    IntervencionEditarWebView,
    SubestadosWebView,
)
from intervenciones.web_api_baja import IntervencionBajaWebView
from intervenciones.web_api import (
    ArchivoEliminarWebView,
    IntervencionDetalleWebView,
    IntervencionesListadoWebView,
)

urlpatterns = [
    path(
        "comedor/<int:pk>/crear/",
        IntervencionCrearWebView.as_view(),
        name="intervenciones_web_crear",
    ),
    path(
        "comedor/<int:comedor_id>/baja/<int:intervencion_id>/",
        IntervencionBajaWebView.as_view(),
        name="intervenciones_web_baja",
    ),
    path(
        "<int:pk>/editar/<int:pk2>/",
        IntervencionEditarWebView.as_view(),
        name="intervenciones_web_editar",
    ),
    path(
        "subestados/",
        SubestadosWebView.as_view(),
        name="intervenciones_web_subestados",
    ),
    path(
        "comedor/<int:pk>/",
        IntervencionesListadoWebView.as_view(),
        name="intervenciones_web_listado",
    ),
    path(
        "<int:pk>/",
        IntervencionDetalleWebView.as_view(),
        name="intervenciones_web_detalle",
    ),
    path(
        "<int:pk>/documentacion/eliminar/",
        ArchivoEliminarWebView.as_view(),
        name="intervenciones_web_archivo_eliminar",
    ),
]
