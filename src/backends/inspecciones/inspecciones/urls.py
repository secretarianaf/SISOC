from django.urls import path

from inspecciones.views import (
    ImportarAsignacionesView,
    ImportarEscuelasView,
    PanelInspeccionesView,
)

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
]
