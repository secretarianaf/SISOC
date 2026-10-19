"""Última muestra completa: el portal conserva sus datos ante fallas remotas."""

from django.db import transaction

from core.internal_services import pedir_json_interno
from dashboard.models import Dashboard

METRIC_KEYS = (
    "cantidad_comedores_activos",
    "cantidad_relevamientos_activos",
    "presupuesto_desayuno",
    "presupuesto_merienda",
    "presupuesto_comida",
)


def actualizar_metricas_comedores(request):
    """Retorna disponibilidad; jamás persiste una respuesta parcial o inválida."""
    if not request.user.has_perm("dashboard.view_dashboard"):
        return False
    response = pedir_json_interno(
        request, "comedores", "/api/comedores/metricas-dashboard/"
    )
    data = response.data
    if response.status != 200 or not isinstance(data, dict):
        return False
    if not all(
        isinstance(data.get(key), int)
        and not isinstance(data[key], bool)
        and -(2**63) <= data[key] < 2**63
        for key in METRIC_KEYS
    ):
        return False
    with transaction.atomic():
        for key in METRIC_KEYS:
            Dashboard.objects.update_or_create(
                llave=key, defaults={"cantidad": data[key]}
            )
    return True
