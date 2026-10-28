"""Métricas del admin: celiaquía (issue #2789)."""

from core.admin_dashboard import Kpi, Seccion, contar_por
from celiaquia.models import Expediente, ExpedienteCiudadano, RegistroErroneo

# Valores de ExpedienteCiudadano.estado_validacion_renaper (ver help_text).
ETIQUETAS_RENAPER = {0: "No validado", 1: "Aceptado", 2: "Rechazado", 3: "Subsanar"}


def metricas():
    legajos = ExpedienteCiudadano.objects.all()
    errores = RegistroErroneo.objects.filter(procesado=False).count()
    return [
        Seccion(
            titulo="Celiaquía",
            kpis=[
                Kpi("Expedientes", Expediente.objects.count()),
                Kpi("Legajos", legajos.count()),
                Kpi(
                    "Registros erróneos sin reprocesar",
                    errores,
                    detalle="Se reprocesan desde el admin del expediente.",
                    alerta=errores > 0,
                ),
            ],
            graficos=[
                contar_por(
                    Expediente.objects.all(), "estado__nombre", "Expedientes por estado"
                ),
                contar_por(legajos, "revision_tecnico", "Legajos por revisión técnica"),
                contar_por(
                    legajos,
                    "estado_validacion_renaper",
                    "Legajos por validación RENAPER",
                    ETIQUETAS_RENAPER,
                ),
                contar_por(legajos, "estado_cupo", "Legajos por cupo"),
            ],
        )
    ]
