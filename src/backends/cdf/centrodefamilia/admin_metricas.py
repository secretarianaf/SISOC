"""Métricas del admin: centros de familia (issue #2789)."""

from core.admin_dashboard import Kpi, Seccion, altas_por_mes, contar_por
from centrodefamilia.models import ParticipanteActividad


def metricas():
    participantes = ParticipanteActividad.objects.all()
    return [
        Seccion(
            titulo="CDF",
            kpis=[Kpi("Participaciones", participantes.count())],
            graficos=[
                contar_por(participantes, "estado", "Participantes por estado"),
                altas_por_mes(participantes, "fecha_registro", "Inscripciones por mes"),
            ],
        )
    ]
