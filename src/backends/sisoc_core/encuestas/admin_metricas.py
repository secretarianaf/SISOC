"""Métricas del admin: encuestas (issue #2789)."""

from core.admin_dashboard import Kpi, Seccion, contar_por
from encuestas.models import Encuesta, EstadoEncuesta


def metricas():
    encuestas = Encuesta.objects.all()
    pendientes = encuestas.filter(estado=EstadoEncuesta.PENDIENTE_APROBACION)
    return [
        Seccion(
            titulo="Encuestas",
            kpis=[
                Kpi("Encuestas", encuestas.count()),
                Kpi("Pendientes de aprobación", pendientes.count()),
            ],
            graficos=[contar_por(encuestas, "estado", "Encuestas por estado")],
        )
    ]
