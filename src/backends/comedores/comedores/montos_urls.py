"""Rutas históricas de Montos de Prestación, conservadas por Comedores."""

from django.urls import path
from core.decorators import permissions_any_required
from comedores.views.montos_prestacion import (
    MontoPrestacionProgramaListView,
    MontoPrestacionProgramaCreateView,
    MontoPrestacionProgramaUpdateView,
    MontoPrestacionProgramaDeleteView,
    MontoPrestacionProgramaDetailView,
)

GRUPOS_MONTO_PRESTACION = ["Gestor prestaciones", "Prestacion"]

urlpatterns = [
    path(
        "montoprestacion/listar",
        permissions_any_required(GRUPOS_MONTO_PRESTACION)(
            MontoPrestacionProgramaListView.as_view()
        ),
        name="montoprestacion_listar",
    ),
    path(
        "montoprestacion/crear",
        permissions_any_required(GRUPOS_MONTO_PRESTACION)(
            MontoPrestacionProgramaCreateView.as_view()
        ),
        name="montoprestacion_crear",
    ),
    path(
        "montoprestacion/<int:pk>/editar",
        permissions_any_required(GRUPOS_MONTO_PRESTACION)(
            MontoPrestacionProgramaUpdateView.as_view()
        ),
        name="montoprestacion_editar",
    ),
    path(
        "montoprestacion/<int:pk>/eliminar",
        permissions_any_required(GRUPOS_MONTO_PRESTACION)(
            MontoPrestacionProgramaDeleteView.as_view()
        ),
        name="montoprestacion_eliminar",
    ),
    path(
        "montoprestacion/<int:pk>/detalle",
        permissions_any_required(GRUPOS_MONTO_PRESTACION)(
            MontoPrestacionProgramaDetailView.as_view()
        ),
        name="montoprestacion_detalle",
    ),
]
