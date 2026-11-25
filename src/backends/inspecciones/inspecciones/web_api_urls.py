"""Rutas de ``/api/web/inspecciones/`` (G1 v1): ver ``inspecciones.web_api``."""

from django.urls import path

from inspecciones.web_api import ActasWebView, InspectoresWebView
from inspecciones.web_api_acta import (
    ActaDetalleWebView,
    AnularActaWebView,
    MarcarPruebaWebView,
)
from inspecciones.web_api_asignaciones import (
    AsignacionesWebView,
    AsignacionNuevaWebView,
    AsignacionQuitarWebView,
    EscuelasBuscarWebView,
    VerificarAsignacionWebView,
)
from inspecciones.web_api_tablero import (
    TableroDatosWebView,
    TableroDescargarWebView,
    TableroExportarWebView,
    TableroWebView,
)
from inspecciones.web_api_escuelas import (
    EscuelaEditarWebView,
    EscuelaNuevaWebView,
    EscuelasWebView,
    LocalidadesWebView,
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
        "asignaciones/",
        AsignacionesWebView.as_view(),
        name="inspecciones_web_asignaciones",
    ),
    path(
        "asignaciones/nueva/",
        AsignacionNuevaWebView.as_view(),
        name="inspecciones_web_asignacion_nueva",
    ),
    path(
        "asignaciones/verificar/",
        VerificarAsignacionWebView.as_view(),
        name="inspecciones_web_asignacion_verificar",
    ),
    path(
        "asignaciones/<int:pk>/quitar/",
        AsignacionQuitarWebView.as_view(),
        name="inspecciones_web_asignacion_quitar",
    ),
    path(
        "escuelas/buscar/",
        EscuelasBuscarWebView.as_view(),
        name="inspecciones_web_escuelas_buscar",
    ),
    path("tablero/", TableroWebView.as_view(), name="inspecciones_web_tablero"),
    path(
        "tablero/datos/",
        TableroDatosWebView.as_view(),
        name="inspecciones_web_tablero_datos",
    ),
    path(
        "tablero/exportar.csv",
        TableroExportarWebView.as_view(),
        name="inspecciones_web_tablero_exportar",
    ),
    path(
        "tablero/descargar-actas/",
        TableroDescargarWebView.as_view(),
        name="inspecciones_web_tablero_descargar",
    ),
    path("escuelas/", EscuelasWebView.as_view(), name="inspecciones_web_escuelas"),
    path(
        "escuelas/nueva/",
        EscuelaNuevaWebView.as_view(),
        name="inspecciones_web_escuela_nueva",
    ),
    path(
        "escuelas/<int:pk>/editar/",
        EscuelaEditarWebView.as_view(),
        name="inspecciones_web_escuela_editar",
    ),
    path(
        "localidades/",
        LocalidadesWebView.as_view(),
        name="inspecciones_web_localidades",
    ),
    path(
        "inspectores/",
        InspectoresWebView.as_view(),
        name="inspecciones_web_inspectores",
    ),
]
