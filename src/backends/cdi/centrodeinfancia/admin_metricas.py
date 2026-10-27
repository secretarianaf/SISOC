"""Métricas del admin: centros de infancia (issue #2789)."""

from core.admin_dashboard import Kpi, Seccion, altas_por_mes, contar_por
from centrodeinfancia.models import AccesoCDI, CentroDeInfancia, NominaCentroInfancia


def metricas():
    nomina = NominaCentroInfancia.objects.all()
    return [
        Seccion(
            titulo="CDI",
            kpis=[
                Kpi("Centros de infancia", CentroDeInfancia.objects.count()),
                Kpi(
                    "Accesos suspendidos",
                    AccesoCDI.objects.filter(
                        estado=AccesoCDI.Estado.SUSPENDIDO
                    ).count(),
                ),
            ],
            graficos=[
                contar_por(AccesoCDI.objects.all(), "estado", "Accesos por estado"),
                contar_por(nomina, "estado", "Nómina por estado"),
                altas_por_mes(nomina, "fecha", "Altas en nómina"),
            ],
        )
    ]
