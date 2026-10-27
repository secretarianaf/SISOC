"""Métricas del admin: PAS y corridas de supervivencia (issue #2789)."""

from core.admin_dashboard import Kpi, Seccion, contar_por
from pas.models import PasPersona, PasSupervivenciaRun


def metricas():
    corridas = PasSupervivenciaRun.objects.all()
    ultima = corridas.order_by("-created_at").first()
    fallidas = corridas.filter(status="failed").count()
    return [
        Seccion(
            titulo="PAS",
            kpis=[
                Kpi("Personas", PasPersona.objects.count()),
                Kpi(
                    "Corridas de supervivencia fallidas",
                    fallidas,
                    detalle=(
                        f"Última: {ultima.status} (corte {ultima.cutoff})"
                        if ultima
                        else "Todavía no hubo corridas."
                    ),
                    alerta=fallidas > 0,
                ),
            ],
            graficos=[
                contar_por(
                    PasPersona.objects.all(), "estado__nombre", "Personas por estado"
                ),
                contar_por(corridas, "status", "Corridas por estado"),
            ],
        )
    ]
