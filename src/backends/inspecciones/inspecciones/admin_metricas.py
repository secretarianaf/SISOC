"""Métricas del admin: inspecciones escolares (issue #2789)."""

from core.admin_dashboard import Kpi, Seccion, altas_por_mes, contar_por
from inspecciones.models import Acta


def metricas():
    actas = Acta.objects.filter(es_prueba=False)
    pendientes = actas.filter(
        notificacion_estado=Acta.EstadoNotificacion.PENDIENTE
    ).count()
    return [
        Seccion(
            titulo="Inspecciones",
            kpis=[
                Kpi("Actas (sin pruebas)", actas.count()),
                Kpi("Notificaciones pendientes", pendientes),
            ],
            graficos=[
                contar_por(actas, "estado", "Actas por estado"),
                altas_por_mes(actas, "fecha_visita", "Actas por mes de visita"),
            ],
        )
    ]
