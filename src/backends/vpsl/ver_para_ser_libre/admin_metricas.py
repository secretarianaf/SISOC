"""Métricas del admin: Ver Para Ser Libres (issue #2789)."""

from core.admin_dashboard import Kpi, Seccion, contar_por
from ver_para_ser_libre.models import ItinerarioVPSL, JornadaVPSL


def metricas():
    itinerarios = ItinerarioVPSL.objects.all()
    jornadas = JornadaVPSL.objects.all()
    return [
        Seccion(
            titulo="VPSL",
            kpis=[
                Kpi("Itinerarios", itinerarios.count()),
                Kpi("Jornadas", jornadas.count()),
            ],
            graficos=[
                contar_por(itinerarios, "estado", "Itinerarios por estado"),
                contar_por(jornadas, "estado", "Jornadas por estado"),
            ],
        )
    ]
