"""Admin de Inspecciones escolares.

El catálogo y las asignaciones se editan aquí o se importan desde el panel del
backoffice (``/inspecciones/``). Inspecciones, actas, notificaciones y eventos
son de sólo lectura: el acta es inmutable y su historial es evidencia.
"""

from django.contrib import admin
from import_export import resources

from core.admin_import_export import BaseImportExportAdmin
from inspecciones.models import (
    Acta,
    AsignacionEscuela,
    Escuela,
    EventoInspeccion,
    Inspeccion,
    NotificacionPapel,
)


class EscuelaResource(resources.ModelResource):
    class Meta:
        model = Escuela
        import_id_fields = ("codigo",)
        fields = (
            "codigo",
            "nombre",
            "cue",
            "distrito",
            "localidad",
            "domicilio",
            "nivel",
        )
        skip_unchanged = True
        report_skipped = True


@admin.register(Escuela)
class EscuelaAdmin(BaseImportExportAdmin):
    resource_classes = [EscuelaResource]
    list_display = ("nombre", "cue", "provincia", "localidad", "distrito", "a_revisar")
    list_filter = ("a_revisar", "provincia", "nivel")
    search_fields = ("nombre", "cue", "codigo", "domicilio", "localidad")
    list_select_related = ("provincia",)
    # Hay ~15.000 localidades: sin raw_id el formulario arma un select enorme.
    raw_id_fields = ("localidad_vinculada",)


@admin.register(AsignacionEscuela)
class AsignacionEscuelaAdmin(admin.ModelAdmin):
    list_display = ("fecha", "escuela", "inspector")
    list_filter = ("fecha",)
    search_fields = ("escuela__nombre", "escuela__cue", "inspector__username")
    autocomplete_fields = ("escuela",)
    raw_id_fields = ("inspector",)


class SoloLecturaAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Inspeccion)
class InspeccionAdmin(SoloLecturaAdmin):
    list_display = ("uuid", "inspector", "estado", "escuela", "fecha_visita", "turno")
    list_filter = ("estado", "fecha_visita", "turno")
    search_fields = ("uuid", "inspector__username", "escuela__nombre")


@admin.register(Acta)
class ActaAdmin(SoloLecturaAdmin):
    list_display = (
        "numero",
        "inspector",
        "escuela",
        "fecha_visita",
        "turno",
        "estado",
        "notificacion_estado",
    )
    list_filter = ("estado", "notificacion_estado", "fecha_visita", "turno")
    search_fields = ("numero", "inspector__username", "escuela__nombre")


@admin.register(NotificacionPapel)
class NotificacionPapelAdmin(SoloLecturaAdmin):
    list_display = ("acta", "version", "condicion_firma", "cargada_at")
    search_fields = ("acta__numero",)


@admin.register(EventoInspeccion)
class EventoInspeccionAdmin(SoloLecturaAdmin):
    list_display = ("at", "accion", "actor_nombre", "inspeccion", "acta")
    list_filter = ("accion",)
