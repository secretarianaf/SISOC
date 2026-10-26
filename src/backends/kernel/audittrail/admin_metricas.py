"""Métricas del admin: actividad reciente de auditoría (issue #2789)."""

from datetime import timedelta

from auditlog.models import LogEntry
from django.utils import timezone

from core.admin_dashboard import Kpi, Seccion, contar_por
from audittrail.models import AuditoriaSesionPWA


def metricas():
    hace_7_dias = timezone.now() - timedelta(days=7)
    eventos = LogEntry.objects.filter(timestamp__gte=hace_7_dias)
    operaciones_admin = eventos.filter(additional_data__origen="admin")
    logins_fallidos = AuditoriaSesionPWA.objects.filter(
        fecha_evento__gte=hace_7_dias, resultado=AuditoriaSesionPWA.RESULTADO_ERROR
    ).count()
    return [
        Seccion(
            titulo="Auditoría (últimos 7 días)",
            kpis=[
                Kpi("Eventos de auditoría", eventos.count()),
                Kpi("Operaciones desde el admin", operaciones_admin.count()),
                Kpi("Ingresos PWA con error", logins_fallidos),
            ],
            graficos=[
                contar_por(
                    eventos, "action", "Eventos por tipo", dict(LogEntry.Action.choices)
                ),
                contar_por(
                    operaciones_admin,
                    "content_type__model",
                    "Operaciones del admin por modelo",
                ),
            ],
        )
    ]
