from django.contrib import admin
from unfold.contrib.filters.admin import (
    AutocompleteSelectFilter,
    ChoicesDropdownFilter,
    RangeDateFilter,
    RangeDateTimeFilter,
)

from core.admin_base import SisocModelAdmin
from core.admin_operaciones import Operacion, OperacionesAdminMixin
from ciudadanos.services_importacion_masiva_jobs import (
    request_resume_ciudadanos_import_job,
)
from ciudadanos.models import (
    Ciudadano,
    CiudadanosImportJob,
    CiudadanosImportJobRow,
    GrupoFamiliar,
    HistorialTransferencia,
    Interaccion,
    ProgramaTransferencia,
)


@admin.register(Ciudadano)
class CiudadanoAdmin(SisocModelAdmin):
    list_display = (
        "apellido",
        "nombre",
        "tipo_documento",
        "documento",
        "estado_validacion_renaper",
        "requiere_revision_manual",
        "activo",
    )
    search_fields = ("apellido", "nombre", "documento", "cuil_cuit")
    list_filter = (
        "activo",
        "tipo_documento",
        ("estado_validacion_renaper", ChoicesDropdownFilter),
        "requiere_revision_manual",
        ("estado_revision_manual", ChoicesDropdownFilter),
        ("tipo_registro_identidad", ChoicesDropdownFilter),
        "sexo",
        ("creado", RangeDateTimeFilter),
    )
    # Territorio y usuarios son tablas grandes: un <select> con todas las filas
    # vuelve inusable el formulario en PRD.
    autocomplete_fields = (
        "provincia",
        "municipio",
        "localidad",
        "creado_por",
        "modificado_por",
        "deleted_by",
    )
    readonly_fields = ("creado", "modificado")

    def get_readonly_fields(self, request, obj=None):
        readonly = super().get_readonly_fields(request, obj)
        if obj is None:
            return readonly
        # Ciudadano.save() rechaza un cambio de tipo_documento con
        # ValidationError, y save_model() no la traduce a error de formulario:
        # sin esto el admin devuelve un 500 en lugar de un campo no editable.
        return tuple(readonly) + ("tipo_documento",)


@admin.register(GrupoFamiliar)
class GrupoFamiliarAdmin(SisocModelAdmin):
    list_display = ("ciudadano_1", "ciudadano_2", "vinculo", "conviven")
    search_fields = (
        "ciudadano_1__apellido",
        "ciudadano_1__nombre",
        "ciudadano_2__apellido",
        "ciudadano_2__nombre",
    )
    list_filter = ("vinculo", "estado_relacion", "conviven", "cuidador_principal")
    autocomplete_fields = ("ciudadano_1", "ciudadano_2")
    list_select_related = ("ciudadano_1", "ciudadano_2")


@admin.register(ProgramaTransferencia)
class ProgramaTransferenciaAdmin(SisocModelAdmin):
    list_display = (
        "ciudadano",
        "tipo",
        "categoria",
        "monto",
        "cantidad_texto",
        "activo",
    )
    search_fields = ("ciudadano__apellido", "ciudadano__nombre", "ciudadano__documento")
    list_filter = ("tipo", "categoria", "activo")
    autocomplete_fields = ("ciudadano",)
    list_select_related = ("ciudadano",)
    readonly_fields = ("creado", "modificado")


@admin.register(HistorialTransferencia)
class HistorialTransferenciaAdmin(SisocModelAdmin):
    list_display = (
        "ciudadano",
        "mes",
        "anio",
        "monto_auh",
        "monto_prestacion_alimentar",
        "monto_centro_familia",
        "monto_comedor",
    )
    search_fields = ("ciudadano__apellido", "ciudadano__nombre", "ciudadano__documento")
    list_filter = ("anio", "mes")
    autocomplete_fields = ("ciudadano",)
    list_select_related = ("ciudadano",)
    readonly_fields = ("creado", "modificado")


@admin.register(Interaccion)
class InteraccionAdmin(SisocModelAdmin):
    list_display = ("ciudadano", "tipo", "fecha", "responsable", "estado")
    search_fields = ("ciudadano__apellido", "ciudadano__nombre", "tipo")
    list_filter = ("estado", ("fecha", RangeDateFilter))
    autocomplete_fields = ("ciudadano", "responsable")
    list_select_related = ("ciudadano", "responsable")
    readonly_fields = ("creado", "modificado")


def _reanudar_importacion(job, _usuario, _datos):
    return request_resume_ciudadanos_import_job(job=job)


@admin.register(CiudadanosImportJob)
class CiudadanosImportJobAdmin(OperacionesAdminMixin, SisocModelAdmin):
    operaciones = (
        Operacion(
            slug="reanudar",
            titulo="Reanudar lote fallido",
            descripcion=(
                "Vuelve el lote a pendiente para que el worker siga desde la "
                "última fila procesada. Solo aplica a lotes fallidos."
            ),
            ejecutar=_reanudar_importacion,
            campo_estado="status",
            icono="replay",
        ),
    )
    list_display = (
        "id",
        "requested_by",
        "original_filename",
        "status",
        "total_rows",
        "processed_rows",
        "requested_at",
    )
    list_filter = (
        ("status", ChoicesDropdownFilter),
        ("requested_at", RangeDateTimeFilter),
    )
    search_fields = ("original_filename", "requested_by__username")
    list_select_related = ("requested_by",)
    readonly_fields = (
        "requested_by",
        "original_filename",
        "archivo",
        "status",
        "total_rows",
        "processed_rows",
        "created_rows",
        "existing_rows",
        "failed_rows",
        "pending_rows",
        "next_row_index",
        "last_successful_row",
        "last_successful_documento",
        "last_attempted_row",
        "last_attempted_documento",
        "last_error_message",
        "last_error_type",
        "last_error_at",
        "resume_count",
        "requested_at",
        "started_at",
        "finished_at",
        "last_activity_at",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        # Sin edición del registro: el formulario queda de solo lectura. El
        # permiso a nivel modelo (obj=None) habilita las operaciones.
        return obj is None and super().has_change_permission(request)


@admin.register(CiudadanosImportJobRow)
class CiudadanosImportJobRowAdmin(SisocModelAdmin):
    list_display = ("job", "fila", "documento_raw", "status", "processed_at")
    list_filter = (
        ("job", AutocompleteSelectFilter),
        ("status", ChoicesDropdownFilter),
        ("processed_at", RangeDateTimeFilter),
    )
    search_fields = ("documento_raw", "dni", "cuil")
    list_select_related = ("job",)
    raw_id_fields = ("job", "ciudadano")
    readonly_fields = (
        "job",
        "fila",
        "documento_raw",
        "dni",
        "cuil",
        "sexo",
        "sexos_intentados",
        "status",
        "ciudadano",
        "mensaje",
        "error_type",
        "attempts",
        "processed_at",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
