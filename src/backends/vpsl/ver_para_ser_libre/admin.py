from django.contrib import admin
from unfold.contrib.filters.admin import (
    ChoicesDropdownFilter,
    RangeDateFilter,
    RangeDateTimeFilter,
)

from core.admin_base import SisocModelAdmin
from core.admin_operaciones import Operacion, OperacionesAdminMixin
from ver_para_ser_libre.models import (
    CasoLaboratorioVPSL,
    ChecklistJornadaVPSL,
    CierreDiarioVPSL,
    HistorialChecklistSedeVPSL,
    HistorialCierreDiarioVPSL,
    HistorialEstadoVPSL,
    HistorialLaboratorioVPSL,
    ItinerarioVPSL,
    EvaluacionSedeItinerarioVPSL,
    JornadaVPSL,
    RegistroNominalVPSL,
    SedeVPSL,
    VehiculoVPSL,
)
from ver_para_ser_libre.services import workflow

# Operaciones de soporte (issue #2789). Cada una llama a la función de
# ``services/workflow.py`` que usa el botón equivalente de la pantalla, con su
# validación de transición. ``workflow.cambiar_estado`` no se expone: acepta
# cualquier estado destino. El motivo del form viaja como ``observacion`` y
# queda en ``HistorialEstadoVPSL``.


def aprobar_itinerario(itinerario, usuario, datos):
    workflow.aprobar_itinerario(
        itinerario, usuario=usuario, observacion=datos.get("motivo", "")
    )


def rechazar_itinerario(itinerario, usuario, datos):
    workflow.rechazar_itinerario(
        itinerario, usuario=usuario, observacion=datos.get("motivo", "")
    )


def enviar_itinerario_a_subsanacion(itinerario, usuario, datos):
    workflow.enviar_itinerario_a_subsanacion(
        itinerario, usuario=usuario, observacion=datos.get("motivo", "")
    )


def cerrar_itinerario(itinerario, usuario, _datos):
    workflow.cerrar_itinerario(itinerario, usuario=usuario)


def habilitar_jornada(jornada, usuario, _datos):
    workflow.habilitar_jornada(jornada, usuario=usuario)


def cerrar_jornada_definitivamente(jornada, usuario, _datos):
    workflow.cerrar_jornada_definitivamente(jornada, usuario=usuario)


class SoloLecturaAdmin(SisocModelAdmin):
    """Historiales: son evidencia del flujo, se consultan y no se editan."""

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ItinerarioVPSL)
class ItinerarioVPSLAdmin(OperacionesAdminMixin, SisocModelAdmin):
    list_display = (
        "id",
        "codigo",
        "provincia",
        "fecha_inicio",
        "fecha_fin",
        "estado",
    )
    list_filter = (
        ("estado", ChoicesDropdownFilter),
        "provincia",
        ("fecha_inicio", RangeDateFilter),
        ("created_at", RangeDateTimeFilter),
    )
    list_select_related = ("provincia",)
    search_fields = (
        "=id",
        "codigo",
        "referente_nombre",
        "referente_apellido",
        "localidades_tentativas",
    )
    operaciones = (
        Operacion(
            slug="aprobar",
            titulo="Aprobar itinerario",
            descripcion=(
                "Requiere itinerario presentado o subsanado, evaluación de sedes "
                "completa y al menos una carta aprobada."
            ),
            ejecutar=aprobar_itinerario,
            campo_estado="estado",
            icono="check_circle",
        ),
        Operacion(
            slug="rechazar",
            titulo="Rechazar itinerario",
            descripcion="Estado final: el itinerario rechazado no vuelve a revisión.",
            ejecutar=rechazar_itinerario,
            campo_estado="estado",
            motivo_obligatorio=True,
            destructiva=True,
            icono="cancel",
        ),
        Operacion(
            slug="enviar_subsanacion",
            titulo="Enviar a subsanación",
            descripcion=(
                "Devuelve el itinerario a Provincia. El motivo es lo que tiene "
                "que subsanar."
            ),
            ejecutar=enviar_itinerario_a_subsanacion,
            campo_estado="estado",
            motivo_obligatorio=True,
            icono="undo",
        ),
        Operacion(
            slug="cerrar",
            titulo="Cerrar itinerario",
            descripcion=(
                "Cierre final. Requiere todas las jornadas finalizadas y sin "
                "casos de laboratorio pendientes."
            ),
            ejecutar=cerrar_itinerario,
            campo_estado="estado",
            motivo_obligatorio=True,
            destructiva=True,
            icono="lock",
        ),
    )


@admin.register(JornadaVPSL)
class JornadaVPSLAdmin(OperacionesAdminMixin, SisocModelAdmin):
    list_display = ("id", "itinerario", "fecha", "sede", "localidad", "estado")
    list_filter = (("estado", ChoicesDropdownFilter), ("fecha", RangeDateFilter))
    list_select_related = ("itinerario__provincia", "localidad")
    search_fields = (
        "=id",
        "sede",
        "referente_nombre",
        "referente_dni",
        "itinerario__codigo",
    )
    raw_id_fields = ("itinerario", "sede_vpsl", "municipio", "localidad")
    operaciones = (
        Operacion(
            slug="habilitar",
            titulo="Habilitar jornada",
            descripcion="Requiere el checklist crítico de la sede completo.",
            ejecutar=habilitar_jornada,
            campo_estado="estado",
            icono="play_circle",
        ),
        Operacion(
            slug="cerrar_definitivamente",
            titulo="Cerrar jornada definitivamente",
            descripcion=(
                "Cierre definitivo: requiere cierre diario consistente con los "
                "registros nominales. No se puede reabrir."
            ),
            ejecutar=cerrar_jornada_definitivamente,
            campo_estado="estado",
            motivo_obligatorio=True,
            destructiva=True,
            icono="lock",
        ),
    )


@admin.register(VehiculoVPSL)
class VehiculoVPSLAdmin(SisocModelAdmin):
    list_display = ("id", "nombre", "orden", "activo")
    list_editable = ("orden", "activo")
    list_filter = ("activo",)
    search_fields = ("nombre",)
    actions = None

    def has_delete_permission(self, request, obj=None):
        if obj is not None and obj.jornadas.exists():
            return False
        return super().has_delete_permission(request, obj)


@admin.register(SedeVPSL)
class SedeVPSLAdmin(SisocModelAdmin):
    list_display = ("nombre", "cueanexo", "jurisdiccion", "localidad", "domicilio")
    list_filter = ("jurisdiccion", "checklist_aprobado")
    search_fields = ("=id", "nombre", "cueanexo", "localidad", "domicilio")


@admin.register(RegistroNominalVPSL)
class RegistroNominalVPSLAdmin(SisocModelAdmin):
    list_display = (
        "id",
        "dni",
        "apellido",
        "nombre",
        "numero_acta",
        "jornada",
        "resultado",
        "estado",
        "fecha_atencion",
    )
    list_filter = (
        ("estado", ChoicesDropdownFilter),
        ("resultado", ChoicesDropdownFilter),
        "validado_renaper",
        ("fecha_atencion", RangeDateFilter),
    )
    list_select_related = ("jornada",)
    search_fields = ("=id", "dni", "apellido", "nombre", "numero_acta")
    raw_id_fields = ("jornada",)


@admin.register(CasoLaboratorioVPSL)
class CasoLaboratorioVPSLAdmin(SisocModelAdmin):
    # Sin operaciones: avanzar el caso pide fecha y responsable del paso
    # (workflow.avanzar_estado_laboratorio); queda pendiente (issue #2789).
    list_display = (
        "id",
        "registro",
        "estado",
        "fecha_envio",
        "fecha_recepcion",
        "fecha_entrega",
    )
    list_filter = (
        ("estado", ChoicesDropdownFilter),
        ("fecha_envio", RangeDateFilter),
        ("fecha_entrega", RangeDateFilter),
    )
    list_select_related = ("registro",)
    search_fields = (
        "=id",
        "registro__dni",
        "registro__apellido",
        "registro__numero_acta",
    )
    raw_id_fields = ("registro",)


@admin.register(ChecklistJornadaVPSL)
class ChecklistJornadaVPSLAdmin(SisocModelAdmin):
    list_display = ("id", "jornada", "sede", "item", "critico", "cumple")
    list_filter = ("item", "critico", "cumple")
    list_select_related = ("jornada", "sede")
    search_fields = ("=id", "jornada__sede", "sede__nombre", "sede__cueanexo")
    raw_id_fields = ("jornada", "sede")


@admin.register(CierreDiarioVPSL)
class CierreDiarioVPSLAdmin(SisocModelAdmin):
    list_display = (
        "id",
        "jornada",
        "fecha_cierre",
        "consistente",
        "cantidad_atenciones_registradas",
    )
    list_filter = ("consistente", ("fecha_cierre", RangeDateTimeFilter))
    list_select_related = ("jornada",)
    search_fields = ("=id", "jornada__sede", "responsable_cierre")
    raw_id_fields = ("jornada",)


@admin.register(EvaluacionSedeItinerarioVPSL)
class EvaluacionSedeItinerarioVPSLAdmin(SisocModelAdmin):
    list_display = ("id", "itinerario", "sede", "estado", "updated_at")
    list_filter = (("estado", ChoicesDropdownFilter),)
    list_select_related = ("itinerario__provincia", "sede")
    search_fields = ("=id", "itinerario__codigo", "sede__nombre", "sede__cueanexo")
    raw_id_fields = ("itinerario", "sede")


@admin.register(HistorialEstadoVPSL)
class HistorialEstadoVPSLAdmin(SoloLecturaAdmin):
    list_display = (
        "created_at",
        "content_type",
        "object_id",
        "estado_anterior",
        "estado_nuevo",
        "usuario",
    )
    list_filter = (
        "content_type",
        "estado_nuevo",
        ("created_at", RangeDateTimeFilter),
    )
    list_select_related = ("content_type", "usuario")
    search_fields = ("=object_id", "observacion", "usuario__username")


@admin.register(HistorialChecklistSedeVPSL)
class HistorialChecklistSedeVPSLAdmin(SoloLecturaAdmin):
    list_display = ("created_at", "checklist", "cumple_anterior", "cumple_nuevo")
    list_filter = (("created_at", RangeDateTimeFilter),)
    list_select_related = ("checklist__jornada", "checklist__sede")
    search_fields = ("=checklist__id",)


@admin.register(HistorialLaboratorioVPSL)
class HistorialLaboratorioVPSLAdmin(SoloLecturaAdmin):
    list_display = ("created_at", "caso", "estado_anterior", "estado_nuevo", "fecha")
    list_filter = ("estado_nuevo", ("fecha", RangeDateFilter))
    list_select_related = ("caso__registro",)
    search_fields = ("=caso__id", "caso__registro__dni", "responsable")


@admin.register(HistorialCierreDiarioVPSL)
class HistorialCierreDiarioVPSLAdmin(SoloLecturaAdmin):
    list_display = ("created_at", "cierre", "responsable", "usuario")
    list_filter = (("created_at", RangeDateTimeFilter),)
    list_select_related = ("cierre__jornada", "usuario")
    search_fields = ("=cierre__id", "responsable")
