from django.urls import path

from inspecciones.views import (
    ImportarAsignacionesView,
    ImportarEscuelasView,
    PanelInspeccionesView,
)
from inspecciones.views_anulacion import AnularActaView, MarcarPruebaActaView

urlpatterns = [
    path("", PanelInspeccionesView.as_view(), name="inspecciones_panel"),
    path(
        "escuelas/importar/",
        ImportarEscuelasView.as_view(),
        name="inspecciones_importar_escuelas",
    ),
    path(
        "asignaciones/importar/",
        ImportarAsignacionesView.as_view(),
        name="inspecciones_importar_asignaciones",
    ),
    path(
        "actas/<str:numero>/anular/",
        AnularActaView.as_view(),
        name="inspecciones_anular_acta",
    ),
    path(
        "actas/<str:numero>/prueba/",
        MarcarPruebaActaView.as_view(),
        name="inspecciones_marcar_prueba_acta",
    ),
]
