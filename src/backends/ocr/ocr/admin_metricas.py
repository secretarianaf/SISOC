"""Métricas del admin: trabajos de OCR (issue #2789)."""

from core.admin_dashboard import Kpi, Seccion, contar_por
from ocr.models import OCRJob


def metricas():
    jobs = OCRJob.objects.all()
    fallidos = jobs.filter(status=OCRJob.Status.FAILED).count()
    return [
        Seccion(
            titulo="OCR",
            kpis=[
                Kpi("Trabajos de OCR", jobs.count()),
                Kpi("Fallidos", fallidos, alerta=fallidos > 0),
            ],
            graficos=[contar_por(jobs, "status", "Trabajos por estado")],
        )
    ]
