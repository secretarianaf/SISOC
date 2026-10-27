from django.contrib import admin
from django.contrib import messages
from unfold.contrib.filters.admin import (
    RangeDateFilter,
    RangeDateTimeFilter,
)

from core.admin_base import SisocModelAdmin, SoloLecturaAdmin
from pas.models import (
    PasAviso,
    PasCircuitoMensual,
    PasControlRenaper,
    PasDeclaracionJurada,
    PasEstado,
    PasExportacionTokens,
    PasHistorialEstado,
    PasIncompatibilidad,
    PasInforme,
    PasInvitacionDDJJ,
    PasPersona,
    PasSupervivenciaBatch,
    PasSupervivenciaRun,
)
from pas.services.ddjj_service import regenerar_invitacion


@admin.register(PasEstado)
class PasEstadoAdmin(SisocModelAdmin):
    list_display = ("nombre", "descripcion")
    search_fields = ("nombre", "descripcion")


@admin.register(PasAviso)
class PasAvisoAdmin(SisocModelAdmin):
    list_display = ("codigo", "descripcion", "observacion")
    list_filter = ("estados",)
    search_fields = ("codigo", "descripcion")
    filter_horizontal = ("estados",)


@admin.register(PasPersona)
class PasPersonaAdmin(SisocModelAdmin):
    list_display = ("id_persona", "apellidos", "nombres", "dni", "provincia", "estado")
    list_filter = ("estado", "provincia", ("fecha_creacion", RangeDateTimeFilter))
    list_select_related = ("provincia", "estado")
    search_fields = ("id_persona", "apellidos", "nombres", "dni", "cuit")
    filter_horizontal = ("avisos",)
    actions = ("regenerar_token_ddjj",)

    @admin.action(description="Regenerar token vigente de DDJJ")
    def regenerar_token_ddjj(self, request, queryset):
        cantidad = 0
        for persona in queryset.iterator():
            regenerar_invitacion(persona, usuario=request.user)
            cantidad += 1
        self.message_user(
            request,
            f"Se regeneraron {cantidad} token(s) de DDJJ.",
            level=messages.SUCCESS,
        )


@admin.register(PasHistorialEstado)
class PasHistorialEstadoAdmin(SisocModelAdmin):
    list_display = ("persona", "estado_anterior", "estado_nuevo", "fecha_cambio")
    list_filter = ("estado_nuevo", ("fecha_cambio", RangeDateTimeFilter))
    list_select_related = ("persona", "estado_anterior", "estado_nuevo")
    search_fields = ("persona__apellidos", "persona__nombres", "persona__dni")
    filter_horizontal = ("avisos_anteriores", "avisos_nuevos")


@admin.register(PasInforme)
class PasInformeAdmin(SisocModelAdmin):
    list_display = ("numero", "usuario", "creado", "total_personas", "total_cambios")
    list_filter = (("creado", RangeDateTimeFilter), "usuario")
    list_select_related = ("usuario",)
    search_fields = (
        "id",
        "usuario__username",
        "usuario__first_name",
        "usuario__last_name",
    )
    filter_horizontal = ("personas", "cambios")


@admin.register(PasCircuitoMensual)
class PasCircuitoMensualAdmin(SisocModelAdmin):
    list_display = (
        "periodo",
        "fecha_exportacion_sintys",
        "fecha_importacion_sintys",
        "fecha_cierre",
    )
    readonly_fields = (
        "fecha_exportacion_sintys",
        "exportado_por",
        "fecha_importacion_sintys",
        "importado_por",
    )


@admin.register(PasControlRenaper)
class PasControlRenaperAdmin(SisocModelAdmin):
    list_display = ("persona", "fecha_consulta", "resultado", "consultado")
    list_filter = (("fecha_consulta", RangeDateFilter), "resultado")
    list_select_related = ("persona",)
    search_fields = ("persona__dni", "persona__apellidos", "persona__nombres")
    readonly_fields = (
        "persona",
        "fecha_consulta",
        "resultado",
        "sexo_consulta",
        "error_tipo",
        "consultado",
    )


@admin.register(PasIncompatibilidad)
class PasIncompatibilidadAdmin(SisocModelAdmin):
    list_display = (
        "persona",
        "categoria",
        "periodo_impacto",
        "estado",
        "fecha_deteccion",
    )
    list_filter = (
        "categoria",
        ("periodo_impacto", RangeDateFilter),
        "estado",
        ("fecha_deteccion", RangeDateTimeFilter),
    )
    list_select_related = ("persona",)
    search_fields = ("persona__dni", "persona__apellidos", "persona__nombres")


@admin.register(PasInvitacionDDJJ)
class PasInvitacionDDJJAdmin(SisocModelAdmin):
    list_display = ("persona", "token", "creada", "vence", "utilizada", "revocada")
    list_select_related = ("persona",)
    search_fields = ("persona__dni", "persona__apellidos", "persona__nombres")
    readonly_fields = (
        "token",
        "creada",
        "utilizada",
        "revocada",
        "creada_por",
        "persona",
        "vence",
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(PasDeclaracionJurada)
class PasDeclaracionJuradaAdmin(SisocModelAdmin):
    list_display = ("persona", "version", "presentada", "finalizada")
    list_select_related = ("persona",)
    search_fields = ("persona__dni", "persona__apellidos", "persona__nombres")
    readonly_fields = tuple(field.name for field in PasDeclaracionJurada._meta.fields)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(PasExportacionTokens)
class PasExportacionTokensAdmin(SisocModelAdmin):
    list_display = ("fecha", "usuario", "cantidad")
    list_select_related = ("usuario",)
    readonly_fields = ("fecha", "usuario", "cantidad")
    ordering = ("-fecha", "-id")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


# Pedir una corrida (supervivencia_jobs.request_run) es global, no sobre un
# registro: no entra como operación del admin (pendiente, issue #2789).
@admin.register(PasSupervivenciaRun)
class PasSupervivenciaRunAdmin(SoloLecturaAdmin):
    list_display = (
        "id",
        "period",
        "cutoff",
        "status",
        "origin",
        "requested_by",
        "created_at",
        "finished_at",
    )
    list_filter = (
        "status",
        "origin",
        ("period", RangeDateFilter),
        ("created_at", RangeDateTimeFilter),
    )
    list_select_related = ("requested_by",)
    search_fields = ("=id", "requested_by__username")
    ordering = ("-period",)


@admin.register(PasSupervivenciaBatch)
class PasSupervivenciaBatchAdmin(SoloLecturaAdmin):
    list_display = (
        "id",
        "run",
        "status",
        "size",
        "position",
        "attempts",
        "dispatched_at",
        "heartbeat",
    )
    list_filter = ("status", ("dispatched_at", RangeDateTimeFilter))
    list_select_related = ("run",)
    search_fields = ("=id", "=run__id")
    ordering = ("-run_id", "id")

    def get_queryset(self, request):
        # ``persona_ids`` puede tener miles de ids por lote: no viaja al listado.
        return super().get_queryset(request).defer("persona_ids")
