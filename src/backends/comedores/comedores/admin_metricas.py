"""Métricas del admin: espacios comunitarios (issue #2789)."""

from core.admin_dashboard import Kpi, Seccion, altas_por_mes, contar_por
from comedores.models import Comedor


def metricas():
    comedores = Comedor.objects.all()
    return [
        Seccion(
            titulo="Comedores",
            kpis=[
                Kpi("Espacios comunitarios", comedores.count()),
                Kpi(
                    "Validación pendiente",
                    comedores.filter(estado_validacion="Pendiente").count(),
                ),
            ],
            graficos=[
                contar_por(comedores, "estado", "Comedores por estado"),
                contar_por(comedores, "estado_validacion", "Comedores por validación"),
                altas_por_mes(comedores, "fecha_creacion", "Altas de comedores"),
            ],
        )
    ]
