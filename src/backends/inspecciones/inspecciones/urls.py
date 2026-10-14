"""Rutas del panel de Inspecciones escolares (``/inspecciones/``)."""

from django.urls import path

from inspecciones.views_actas import (
    ActaArchivoNotificacionView,
    ActaDetalleView,
    ActaImagenView,
    ActaPdfView,
    ActasView,
)
from inspecciones.views_ajax import (
    EscuelasAjaxView,
    InspectoresAjaxView,
    LocalidadesAjaxView,
    VerificarAsignacionAjaxView,
)
from inspecciones.views_asignaciones import (
    AsignacionCrearView,
    AsignacionesView,
    AsignacionQuitarView,
)
from inspecciones.views_escuelas import (
    EscuelaCrearView,
    EscuelaEditarView,
    EscuelasView,
)
from inspecciones.views_importacion import (
    CancelarView,
    ConfirmarView,
    ObservacionesCSVView,
    RevisionView,
    SubirArchivoView,
)
from inspecciones.views_tablero import (
    TableroDatosView,
    TableroExportarView,
    TableroView,
)


def _rutas_de_importacion(tipo):
    prefijo = f"{tipo}/importar/"
    nombre = f"inspecciones_importar_{tipo}"
    return [
        path(prefijo, SubirArchivoView.as_view(tipo=tipo), name=nombre),
        path(
            f"{prefijo}<str:token>/",
            RevisionView.as_view(tipo=tipo),
            name=f"{nombre}_revision",
        ),
        path(
            f"{prefijo}<str:token>/confirmar/",
            ConfirmarView.as_view(tipo=tipo),
            name=f"{nombre}_confirmar",
        ),
        path(
            f"{prefijo}<str:token>/cancelar/",
            CancelarView.as_view(tipo=tipo),
            name=f"{nombre}_cancelar",
        ),
        path(
            f"{prefijo}<str:token>/observaciones.csv",
            ObservacionesCSVView.as_view(tipo=tipo),
            name=f"{nombre}_observaciones",
        ),
    ]


urlpatterns = [
    path("", EscuelasView.as_view(), name="inspecciones_panel"),
    path(
        "escuelas/nueva/",
        EscuelaCrearView.as_view(),
        name="inspecciones_escuela_nueva",
    ),
    path(
        "escuelas/<int:pk>/editar/",
        EscuelaEditarView.as_view(),
        name="inspecciones_escuela_editar",
    ),
    *_rutas_de_importacion("escuelas"),
    path(
        "asignaciones/",
        AsignacionesView.as_view(),
        name="inspecciones_asignaciones",
    ),
    path(
        "asignaciones/nueva/",
        AsignacionCrearView.as_view(),
        name="inspecciones_asignacion_nueva",
    ),
    path(
        "asignaciones/<int:pk>/quitar/",
        AsignacionQuitarView.as_view(),
        name="inspecciones_asignacion_quitar",
    ),
    *_rutas_de_importacion("asignaciones"),
    path("actas/", ActasView.as_view(), name="inspecciones_actas"),
    path(
        "actas/<str:numero>/",
        ActaDetalleView.as_view(),
        name="inspecciones_acta_detalle",
    ),
    path(
        "actas/<str:numero>/pdf/",
        ActaPdfView.as_view(),
        name="inspecciones_acta_pdf",
    ),
    path(
        "actas/<str:numero>/imagenes/<uuid:imagen_uuid>/",
        ActaImagenView.as_view(),
        name="inspecciones_acta_imagen",
    ),
    path(
        "actas/<str:numero>/notificaciones/<uuid:archivo_uuid>/",
        ActaArchivoNotificacionView.as_view(),
        name="inspecciones_acta_notificacion_archivo",
    ),
    path(
        "ajax/localidades/",
        LocalidadesAjaxView.as_view(),
        name="inspecciones_ajax_localidades",
    ),
    path(
        "ajax/inspectores/",
        InspectoresAjaxView.as_view(),
        name="inspecciones_ajax_inspectores",
    ),
    path(
        "ajax/escuelas/",
        EscuelasAjaxView.as_view(),
        name="inspecciones_ajax_escuelas",
    ),
    path(
        "ajax/asignaciones/verificar/",
        VerificarAsignacionAjaxView.as_view(),
        name="inspecciones_ajax_verificar_asignacion",
    ),
    path("tablero/", TableroView.as_view(), name="inspecciones_tablero"),
    path(
        "tablero/datos/",
        TableroDatosView.as_view(),
        name="inspecciones_tablero_datos",
    ),
    path(
        "tablero/exportar.csv",
        TableroExportarView.as_view(),
        name="inspecciones_tablero_exportar",
    ),
]
