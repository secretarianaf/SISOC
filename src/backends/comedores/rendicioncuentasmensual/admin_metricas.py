"""Métricas del admin: rendiciones de cuentas mensuales (issue #2789)."""

from core.admin_dashboard import Kpi, Seccion, altas_por_mes, contar_por
from rendicioncuentasmensual.models import RendicionCuentaMensual


def metricas():
    rendiciones = RendicionCuentaMensual.objects.all()
    return [
        Seccion(
            titulo="Rendiciones mensuales",
            kpis=[Kpi("Rendiciones", rendiciones.count())],
            graficos=[
                contar_por(rendiciones, "estado", "Rendiciones por estado"),
                altas_por_mes(rendiciones, "fecha_creacion", "Rendiciones por mes"),
            ],
        )
    ]
