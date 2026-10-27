"""Métricas del admin: VAT (issue #2789)."""

from core.admin_dashboard import Kpi, Seccion, altas_por_mes, contar_por
from VAT.models import Inscripcion, Voucher


def metricas():
    inscripciones = Inscripcion.objects.all()
    vouchers = Voucher.objects.all()
    return [
        Seccion(
            titulo="VAT",
            kpis=[
                Kpi("Inscripciones", inscripciones.count()),
                Kpi("Vouchers activos", vouchers.filter(estado="activo").count()),
            ],
            graficos=[
                contar_por(inscripciones, "estado", "Inscripciones por estado"),
                contar_por(vouchers, "estado", "Vouchers por estado"),
                altas_por_mes(
                    inscripciones, "fecha_inscripcion", "Inscripciones por mes"
                ),
            ],
        )
    ]
