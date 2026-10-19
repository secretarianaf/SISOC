"""Administracion de la auditoria de autenticacion compartida."""

from django.contrib import admin

from audittrail.models import AuditoriaSesionPWA


@admin.register(AuditoriaSesionPWA)
class AuditoriaSesionPWAAdmin(admin.ModelAdmin):
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
