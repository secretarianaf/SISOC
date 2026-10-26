from django.contrib import admin
from unfold.contrib.filters.admin import RangeDateTimeFilter

from core.admin_base import SisocModelAdmin
from importarexpediente.models import (
    ArchivosImportados,
    ErroresImportacion,
    ExitoImportacion,
    RegistroImportado,
)


class SoloLecturaAdmin(SisocModelAdmin):
    """Registro de importaciones: se consulta, no se edita desde el admin.

    Aplicar estados por lote no se ofrece como operación: recalcula el estado
    de todos los comedores del programa (presentes y ausentes del lote), no
    solo los del archivo, y repetirlo suma ausencias y cambios de estado.
    """

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ArchivosImportados)
class ArchivosImportadosAdmin(SoloLecturaAdmin):
    list_display = (
        "id",
        "archivo",
        "usuario",
        "fecha_subida",
        "numero_expediente_pago",
        "mes_pago",
        "ano_pago",
        "count_exitos",
        "count_errores",
        "importacion_completada",
    )
    list_select_related = ("usuario",)
    search_fields = (
        "=id",
        "numero_expediente_pago",
        "archivo",
        "usuario__username",
    )
    list_filter = (
        "importacion_completada",
        "ano_pago",
        "mes_pago",
        ("fecha_subida", RangeDateTimeFilter),
    )


class _FilaImportacionAdmin(SoloLecturaAdmin):
    list_display = ("id", "archivo_importado", "fila", "mensaje")
    list_select_related = ("archivo_importado__usuario",)
    search_fields = (
        "=archivo_importado__id",
        "archivo_importado__numero_expediente_pago",
        "mensaje",
    )
    list_filter = (("archivo_importado__fecha_subida", RangeDateTimeFilter),)


@admin.register(ErroresImportacion)
class ErroresImportacionAdmin(_FilaImportacionAdmin):
    pass


@admin.register(ExitoImportacion)
class ExitoImportacionAdmin(_FilaImportacionAdmin):
    pass


@admin.register(RegistroImportado)
class RegistroImportadoAdmin(SoloLecturaAdmin):
    list_display = ("id", "exito_importacion", "expediente_pago")
    list_select_related = (
        "exito_importacion__archivo_importado__usuario",
        "expediente_pago",
    )
    search_fields = (
        "=exito_importacion__archivo_importado__id",
        "=expediente_pago__id",
        "expediente_pago__expediente_pago",
    )
    raw_id_fields = ("exito_importacion", "expediente_pago")
