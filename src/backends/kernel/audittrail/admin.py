"""Administracion de la auditoria de autenticacion compartida."""

from auditlog.admin import LogEntryAdmin as BaseLogEntryAdmin
from auditlog.models import LogEntry
from django.contrib import admin
from unfold.contrib.filters.admin import RangeDateTimeFilter

from core.admin_base import SisocModelAdmin
from audittrail.models import AuditoriaSesionPWA

# django-auditlog registra LogEntry con el admin clásico; se re-registra con
# Unfold (#2789) conservando su comportamiento de solo lectura.
admin.site.unregister(LogEntry)


@admin.register(LogEntry)
class LogEntryAdmin(BaseLogEntryAdmin, SisocModelAdmin):
    """Eventos de auditlog, buscables por id del registro auditado."""

    list_filter = [
        "action",
        ("timestamp", RangeDateTimeFilter),
        *BaseLogEntryAdmin.list_filter[1:],
    ]
    search_fields = ["object_pk", *BaseLogEntryAdmin.search_fields]


@admin.register(AuditoriaSesionPWA)
class AuditoriaSesionPWAAdmin(SisocModelAdmin):
    list_display = (
        "fecha_evento",
        "evento",
        "resultado",
        "user",
        "username_intentado",
        "codigo_respuesta",
        "ip",
        "platform",
    )
    list_filter = ("evento", "resultado", "platform", "is_standalone")
    search_fields = ("username_intentado", "user__username", "path", "motivo_error")
    readonly_fields = (
        "fecha_evento",
        "user",
        "username_intentado",
        "evento",
        "resultado",
        "ip",
        "user_agent",
        "path",
        "metodo_http",
        "codigo_respuesta",
        "motivo_error",
        "session_id",
        "rol_pwa_snapshot",
        "comedor_ids_snapshot",
        "app_version",
        "platform",
        "is_standalone",
    )
