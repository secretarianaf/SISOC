from django.urls import path

from relevamientos.views.api_views import (
    PrimerSeguimientoApiView,
    RelevamientoApiView,
    RelevamientoPdfOficialApiView,
    SeguimientoApiView,
    SeguimientoPdfOficialApiView,
)

urlpatterns = [
    # TODO: Migrar a router DRF (estilo centrodefamilia).
    path(
        "api/relevamiento",
        RelevamientoApiView.as_view(),
        name="api_relevamiento",
    ),
    path(
        "api/relevamiento/primer-seguimiento",
        PrimerSeguimientoApiView.as_view(),
        name="api_primer_seguimiento",
    ),
    path(
        "api/relevamiento/seguimiento",
        SeguimientoApiView.as_view(),
        name="api_seguimiento",
    ),
    # PDF oficial que arma Gestionar (#2630): HTML autocontenido, SISOC lo convierte.
    path(
        "api/relevamiento/pdf-oficial",
        RelevamientoPdfOficialApiView.as_view(),
        name="api_relevamiento_pdf_oficial",
    ),
    path(
        "api/relevamiento/seguimiento/pdf-oficial",
        SeguimientoPdfOficialApiView.as_view(),
        name="api_seguimiento_pdf_oficial",
    ),
]
