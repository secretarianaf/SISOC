"""Métricas del admin: relevamientos y sincronización con GESTIONAR (issue #2789)."""

from core.admin_dashboard import Kpi, Seccion, altas_por_mes, contar_por
from relevamientos.models import PrimerSeguimiento, Relevamiento


def metricas():
    relevamientos = Relevamiento.objects.all()
    sin_sync_relevamientos = relevamientos.filter(sincronizado_gestionar=False).count()
    sin_sync_seguimientos = PrimerSeguimiento.objects.filter(
        sincronizado_gestionar=False
    ).count()
    return [
        Seccion(
            titulo="Relevamientos",
            kpis=[
                Kpi("Relevamientos", relevamientos.count()),
                Kpi(
                    "Relevamientos sin sincronizar con GESTIONAR",
                    sin_sync_relevamientos,
                    detalle="Se reintentan desde el admin del relevamiento.",
                    alerta=sin_sync_relevamientos > 0,
                ),
                Kpi(
                    "Primeros seguimientos sin sincronizar",
                    sin_sync_seguimientos,
                    alerta=sin_sync_seguimientos > 0,
                ),
            ],
            graficos=[
                contar_por(relevamientos, "estado", "Relevamientos por estado"),
                altas_por_mes(relevamientos, "fecha_creacion", "Relevamientos por mes"),
            ],
        )
    ]
