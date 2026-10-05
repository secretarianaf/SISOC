"""URLs de la API REST de Celiaquia.

Se montan bajo `api/celiaquia/` desde `celiaquia_runtime/urls.py`. En el
deploy separado el core las reenvia al backend porque `api/celiaquia/` esta en
los `url_prefixes` de `src/backends/config/backends.json`.
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from celiaquia.api_views import (
    CupoMovimientoViewSet,
    EstadoExpedienteViewSet,
    EstadoLegajoViewSet,
    ExpedienteViewSet,
    LegajoViewSet,
    OrganismoViewSet,
    PagoExpedienteViewSet,
    ProvinciaCupoViewSet,
    ReporteViewSet,
    TipoCruceViewSet,
    TipoDocumentoViewSet,
)

router = DefaultRouter()
router.register("expedientes", ExpedienteViewSet, basename="celiaquia-expediente")
router.register(r"reporte", ReporteViewSet, basename="celiaquia-reporte")
router.register("legajos", LegajoViewSet, basename="celiaquia-legajo")
router.register("cupos", ProvinciaCupoViewSet, basename="celiaquia-cupo")
router.register(
    "cupos-movimientos", CupoMovimientoViewSet, basename="celiaquia-cupo-movimiento"
)
router.register("pagos", PagoExpedienteViewSet, basename="celiaquia-pago")
router.register(
    "estados-expediente",
    EstadoExpedienteViewSet,
    basename="celiaquia-estado-expediente",
)
router.register(
    "estados-legajo", EstadoLegajoViewSet, basename="celiaquia-estado-legajo"
)
router.register("organismos", OrganismoViewSet, basename="celiaquia-organismo")
router.register("tipos-cruce", TipoCruceViewSet, basename="celiaquia-tipo-cruce")
router.register(
    "tipos-documento", TipoDocumentoViewSet, basename="celiaquia-tipo-documento"
)

urlpatterns = [
    path("", include(router.urls)),
]
