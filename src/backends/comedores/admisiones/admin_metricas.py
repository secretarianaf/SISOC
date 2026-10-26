"""Métricas del admin: admisiones (issue #2789)."""

from core.admin_dashboard import Kpi, Seccion, contar_por
from admisiones.models.admisiones import Admision


def metricas():
    admisiones = Admision.objects.all()
    return [
        Seccion(
            titulo="Admisiones",
            kpis=[
                Kpi("Admisiones", admisiones.count()),
                Kpi("Activas", admisiones.filter(activa=True).count()),
            ],
            graficos=[
                contar_por(admisiones, "estado_admision", "Admisiones por estado"),
                contar_por(admisiones, "estado_legales", "Admisiones por estado legal"),
            ],
        )
    ]
