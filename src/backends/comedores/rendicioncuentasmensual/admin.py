from django.contrib import admin
from unfold.contrib.filters.admin import (
    ChoicesDropdownFilter,
    RangeDateFilter,
    RangeDateTimeFilter,
)

from core.admin_base import SisocModelAdmin
from core.admin_operaciones import Operacion, OperacionesAdminMixin
from rendicioncuentasmensual.models import DocumentacionAdjunta, RendicionCuentaMensual
from rendicioncuentasmensual.services import RendicionCuentaMensualService


# Operaciones de soporte (issue #2789). Igual que la vista de revisión de
# documentos: el service valida que la rendición esté en una etapa de revisión
# en curso, que el documento sea vigente y que "subsanar" traiga observaciones
# (acá, el motivo de la operación).


def validar_documento(documento, usuario, _datos):
    return RendicionCuentaMensualService.actualizar_estado_documento_revision(
        documento=documento,
        estado=DocumentacionAdjunta.ESTADO_VALIDADO,
        actor=usuario,
    )


def subsanar_documento(documento, usuario, datos):
    return RendicionCuentaMensualService.actualizar_estado_documento_revision(
        documento=documento,
        estado=DocumentacionAdjunta.ESTADO_SUBSANAR,
        observaciones=datos.get("motivo"),
        actor=usuario,
    )


@admin.register(RendicionCuentaMensual)
class RendicionCuentaMensualAdmin(SisocModelAdmin):
    list_display = (
        "id",
        "comedor",
        "numero_rendicion",
        "mes",
        "anio",
        "convenio",
        "estado",
        "etapa_proceso",
        "subestado_proceso",
        "ultima_modificacion",
    )
    list_select_related = ("comedor",)
    search_fields = (
        "=id",
        "comedor__nombre",
        "comedor__codigo_de_proyecto",
        "convenio",
        "nombre",
    )
    list_filter = (
        ("estado", ChoicesDropdownFilter),
        ("etapa_proceso", ChoicesDropdownFilter),
        ("subestado_proceso", ChoicesDropdownFilter),
        "linea_programatica",
        "anio",
        "mes",
        ("periodo_inicio", RangeDateFilter),
        ("fecha_creacion", RangeDateTimeFilter),
    )
    raw_id_fields = (
        "proyecto",
        "rendicion_origen_acta",
        "usuario_creador",
        "usuario_ultima_modificacion",
        "comedor",
    )


@admin.register(DocumentacionAdjunta)
class DocumentacionAdjuntaAdmin(OperacionesAdminMixin, SisocModelAdmin):
    list_display = (
        "id",
        "nombre",
        "categoria",
        "estado",
        "revision_estado",
        "rendicion_cuenta_mensual",
        "fecha_creacion",
    )
    list_select_related = ("rendicion_cuenta_mensual",)
    search_fields = (
        "=id",
        "nombre",
        "=rendicion_cuenta_mensual__id",
        "rendicion_cuenta_mensual__comedor__nombre",
    )
    list_filter = (
        ("categoria", ChoicesDropdownFilter),
        "estado",
        "revision_estado",
        ("fecha_creacion", RangeDateTimeFilter),
    )
    raw_id_fields = (
        "rendicion_cuenta_mensual",
        "documento_subsanado",
        "visualizacion_usuario",
    )
    operaciones = (
        Operacion(
            slug="validar_documento",
            titulo="Revisión: marcar documento validado",
            descripcion=(
                "Deja el documento como validado en la revisión en curso. Se "
                "confirma al finalizar la etapa de revisión."
            ),
            ejecutar=validar_documento,
            campo_estado="revision_estado",
            icono="check_circle",
        ),
        Operacion(
            slug="subsanar_documento",
            titulo="Revisión: enviar documento a subsanar",
            descripcion=(
                "Deja el documento a subsanar en la revisión en curso. El motivo "
                "se guarda como observación del documento."
            ),
            ejecutar=subsanar_documento,
            campo_estado="revision_estado",
            motivo_obligatorio=True,
            icono="report",
        ),
    )
