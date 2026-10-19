"""Rutas bajo ``/api/inspecciones/`` (contrato de la PWA Sisoc Inspecciones)."""

from django.urls import path

from inspecciones.api_views import (
    ActaPdfView,
    ActasView,
    ActaView,
    ArchivoNotificacionView,
    BorradoresView,
    BorradorView,
    EscuelaFichaView,
    EscuelasAsignadasView,
    EscuelasBusquedaView,
    FinalizarView,
    ImagenBorradorView,
    ImagenView,
    NotificacionesView,
)

urlpatterns = [
    path(
        "escuelas/asignadas/",
        EscuelasAsignadasView.as_view(),
        name="api_inspecciones_escuelas_asignadas",
    ),
    path(
        "escuelas/",
        EscuelasBusquedaView.as_view(),
        name="api_inspecciones_escuelas_buscar",
    ),
    path(
        "escuelas/<str:codigo>/",
        EscuelaFichaView.as_view(),
        name="api_inspecciones_escuela_ficha",
    ),
    path(
        "borradores/",
        BorradoresView.as_view(),
        name="api_inspecciones_borradores",
    ),
    path(
        "borradores/<uuid:inspeccion_uuid>/",
        BorradorView.as_view(),
        name="api_inspecciones_borrador",
    ),
    path(
        "borradores/<uuid:inspeccion_uuid>/finalizar/",
        FinalizarView.as_view(),
        name="api_inspecciones_finalizar",
    ),
    path(
        "borradores/<uuid:inspeccion_uuid>/imagenes/<uuid:imagen_uuid>/",
        ImagenBorradorView.as_view(),
        name="api_inspecciones_borrador_imagen",
    ),
    path(
        "imagenes/<uuid:imagen_uuid>/",
        ImagenView.as_view(),
        name="api_inspecciones_imagen",
    ),
    path("actas/", ActasView.as_view(), name="api_inspecciones_actas"),
    path("actas/<str:numero>/", ActaView.as_view(), name="api_inspecciones_acta"),
    path(
        "actas/<str:numero>/pdf/",
        ActaPdfView.as_view(),
        name="api_inspecciones_acta_pdf",
    ),
    path(
        "actas/<str:numero>/notificaciones/",
        NotificacionesView.as_view(),
        name="api_inspecciones_acta_notificaciones",
    ),
    path(
        "notificaciones/archivos/<uuid:archivo_uuid>/",
        ArchivoNotificacionView.as_view(),
        name="api_inspecciones_notificacion_archivo",
    ),
]
