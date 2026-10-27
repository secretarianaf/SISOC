"""Métricas del admin: ciudadanos y validación RENAPER (issue #2789)."""

from core.admin_dashboard import Kpi, Seccion, altas_por_mes, contar_por
from ciudadanos.models import Ciudadano, CiudadanosImportJob


def metricas():
    ciudadanos = Ciudadano.objects.all()
    revision_pendiente = ciudadanos.filter(requiere_revision_manual=True).count()
    jobs_fallidos = CiudadanosImportJob.objects.filter(
        status=CiudadanosImportJob.Status.FAILED
    ).count()
    return [
        Seccion(
            titulo="Ciudadanos",
            kpis=[
                Kpi("Ciudadanos", ciudadanos.count()),
                Kpi(
                    "Revisión manual pendiente",
                    revision_pendiente,
                    alerta=revision_pendiente > 0,
                ),
                Kpi(
                    "Importaciones fallidas",
                    jobs_fallidos,
                    detalle="Se reanudan desde el admin del job.",
                    alerta=jobs_fallidos > 0,
                ),
            ],
            graficos=[
                contar_por(
                    ciudadanos, "estado_validacion_renaper", "Validación RENAPER"
                ),
                altas_por_mes(ciudadanos, "creado", "Altas de ciudadanos"),
            ],
        )
    ]
