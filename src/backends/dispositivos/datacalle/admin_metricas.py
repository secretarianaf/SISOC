"""Métricas del admin: relevamientos de situación de calle (issue #2789)."""

from core.admin_dashboard import Kpi, Seccion, contar_por
from datacalle.models import Relevamiento


def metricas():
    relevamientos = Relevamiento.objects.all()
    en_curso = relevamientos.filter(estado=Relevamiento.Estado.EN_CURSO).count()
    return [
        Seccion(
            titulo="Datacalle",
            kpis=[Kpi("Relevamientos en curso", en_curso)],
            graficos=[contar_por(relevamientos, "estado", "Relevamientos por estado")],
        )
    ]
