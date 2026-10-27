from django import forms
from django.contrib import admin
from django.core.exceptions import ValidationError
from unfold.contrib.filters.admin import (
    FieldTextFilter,
    ChoicesDropdownFilter,
    RangeDateTimeFilter,
    RelatedDropdownFilter,
)

from core.admin_base import SisocModelAdmin, SisocTabularInline, SoloLecturaAdminMixin
from core.admin_operaciones import Operacion, OperacionesAdminMixin
from celiaquia.services import registros_erroneos_service
from celiaquia.services.cupo_service import (  # pylint: disable=no-name-in-module
    CupoNoConfigurado,
    CupoService,
)
from celiaquia.services.revision_service import (  # pylint: disable=no-name-in-module
    RevisionService,
)
from .models import (
    EstadoExpediente,
    EstadoLegajo,
    Organismo,
    TipoCruce,
    Expediente,
    ExpedienteCiudadano,
    AsignacionTecnico,
    ExpedienteEstadoHistorial,
    HistorialComentarios,
    TipoDocumento,
    DocumentoLegajo,
    CupoMovimiento,
    CupoTitular,
    HistorialCupo,
    HistorialValidacionTecnica,
    PagoExpediente,
    PagoNomina,
    ProvinciaCupo,
    RegistroErroneo,
    Subsanacion,
    TipoSubsanacion,
    ValidacionRenaper,
)


# Operaciones de soporte (issue #2789). La revisión técnica repite la secuencia
# de RevisarLegajoView.post (sin la rama provincial: el admin es de
# superusuarios) y el cupo llama a CupoService como CupoViewSet._mover_cupo.


def _validar_revision(legajo, usuario, accion):
    RevisionService.verificar_permiso(usuario, legajo.expediente, accion)
    accion = RevisionService.validar_accion(accion)
    RevisionService.validar_transicion(legajo, accion)
    return accion


def aprobar_legajo(legajo, usuario, _datos):
    accion = _validar_revision(legajo, usuario, "APROBAR")
    RevisionService.liberar_cupo_si_corresponde(legajo, usuario, accion)
    return RevisionService.aprobar(legajo, usuario)


def rechazar_legajo(legajo, usuario, datos):
    accion = _validar_revision(legajo, usuario, "RECHAZAR")
    # Sin comentarios técnicos elegidos: el motivo es el texto libre.
    motivo = RevisionService.componer_motivo((), datos.get("motivo", ""))
    RevisionService.liberar_cupo_si_corresponde(legajo, usuario, accion)
    return RevisionService.rechazar(legajo, usuario, motivo, comentarios=())


def subsanar_legajo(legajo, usuario, datos):
    accion = _validar_revision(legajo, usuario, "SUBSANAR")
    motivo = RevisionService.componer_motivo((), datos.get("motivo", ""))
    RevisionService.liberar_cupo_si_corresponde(legajo, usuario, accion)
    # Mismo armado que el formato legacy de la pantalla: un único tipo con el
    # motivo general como detalle.
    tipo = datos.get("tipo_subsanacion") or TipoSubsanacion.OTROS
    return RevisionService.subsanar(
        legajo,
        usuario,
        motivo,
        tipo_subsanacion=tipo,
        comentarios=(),
        observaciones_fallback=[(tipo, motivo)],
    )


def _mover_cupo(movimiento, legajo, usuario, motivo):
    try:
        return movimiento(legajo=legajo, usuario=usuario, motivo=motivo)
    except CupoNoConfigurado as exc:
        raise ValidationError(str(exc)) from exc


def suspender_cupo(legajo, usuario, datos):
    return _mover_cupo(
        CupoService.suspender_slot, legajo, usuario, datos.get("motivo", "")
    )


def liberar_cupo(legajo, usuario, datos):
    return _mover_cupo(
        CupoService.liberar_slot, legajo, usuario, datos.get("motivo", "")
    )


def reactivar_cupo(legajo, usuario, datos):
    return _mover_cupo(
        CupoService.reactivar_slot, legajo, usuario, datos.get("motivo", "")
    )


def reprocesar_registros_erroneos(expediente, usuario, _datos):
    return registros_erroneos_service.reprocesar(expediente, usuario)


def _campos_subsanacion():
    return {
        "tipo_subsanacion": forms.ChoiceField(
            label="Tipo de observación",
            choices=TipoSubsanacion.choices,
            initial=TipoSubsanacion.OTROS,
        )
    }


@admin.register(EstadoExpediente)
class EstadoExpedienteAdmin(SisocModelAdmin):
    list_display = ("nombre",)
    search_fields = ("nombre",)


@admin.register(EstadoLegajo)
class EstadoLegajoAdmin(SisocModelAdmin):
    list_display = ("nombre",)
    search_fields = ("nombre",)


@admin.register(Organismo)
class OrganismoAdmin(SisocModelAdmin):
    list_display = ("nombre",)
    search_fields = ("nombre",)


@admin.register(TipoCruce)
class TipoCruceAdmin(SisocModelAdmin):
    list_display = ("nombre",)
    search_fields = ("nombre",)


@admin.register(Expediente)
class ExpedienteAdmin(OperacionesAdminMixin, SisocModelAdmin):
    list_display = (
        "id",
        "numero_expediente",
        "usuario_provincia",
        "estado",
        "fecha_creacion",
    )
    list_select_related = ("usuario_provincia", "estado")
    list_filter = (
        ("estado", RelatedDropdownFilter),
        ("fecha_creacion", RangeDateTimeFilter),
    )
    search_fields = ("=id", "numero_expediente", "usuario_provincia__username")
    readonly_fields = ("fecha_creacion", "fecha_modificacion", "fecha_cierre")
    raw_id_fields = (
        "usuario_provincia",
        "usuario_modificador",
        "excel_masivo_cargado_por",
        "excel_masivo_procesado_por",
    )
    operaciones = (
        Operacion(
            slug="reprocesar_registros_erroneos",
            titulo="Reprocesar registros erróneos",
            descripcion=(
                "Reintenta crear los legajos de las filas del Excel que "
                "quedaron con error."
            ),
            ejecutar=reprocesar_registros_erroneos,
            en_lote=False,
            icono="restart_alt",
        ),
    )


@admin.register(ExpedienteCiudadano)
class ExpedienteCiudadanoAdmin(OperacionesAdminMixin, SisocModelAdmin):
    list_display = (
        "id",
        "ciudadano",
        "expediente",
        "estado",
        "rol",
        "revision_tecnico",
        "estado_cupo",
        "es_titular_activo",
        "creado_en",
    )
    list_select_related = ("ciudadano", "expediente__usuario_provincia", "estado")
    list_filter = (
        ("revision_tecnico", ChoicesDropdownFilter),
        ("estado_cupo", ChoicesDropdownFilter),
        "es_titular_activo",
        ("estado", RelatedDropdownFilter),
        "rol",
        "resultado_sintys",
        ("creado_en", RangeDateTimeFilter),
    )
    search_fields = (
        "=id",
        "ciudadano__documento",
        "ciudadano__nombre",
        "ciudadano__apellido",
        "=expediente__id",
        "expediente__numero_expediente",
    )
    raw_id_fields = ("deleted_by", "expediente", "ciudadano", "subsanacion_usuario")
    operaciones = (
        Operacion(
            slug="aprobar",
            titulo="Aprobar legajo",
            ejecutar=aprobar_legajo,
            campo_estado="revision_tecnico",
            icono="check_circle",
        ),
        Operacion(
            slug="rechazar",
            titulo="Rechazar legajo",
            ejecutar=rechazar_legajo,
            campo_estado="revision_tecnico",
            motivo_obligatorio=True,
            icono="cancel",
        ),
        Operacion(
            slug="subsanar",
            titulo="Pedir subsanación",
            ejecutar=subsanar_legajo,
            campo_estado="revision_tecnico",
            motivo_obligatorio=True,
            campos=_campos_subsanacion,
            icono="edit_note",
        ),
        Operacion(
            slug="suspender_cupo",
            titulo="Suspender titular (mantiene el cupo)",
            ejecutar=suspender_cupo,
            campo_estado="es_titular_activo",
            motivo_obligatorio=True,
            icono="pause_circle",
        ),
        Operacion(
            slug="reactivar_cupo",
            titulo="Reactivar titular suspendido",
            ejecutar=reactivar_cupo,
            campo_estado="es_titular_activo",
            icono="play_circle",
        ),
        Operacion(
            slug="liberar_cupo",
            titulo="Dar de baja del cupo (libera el lugar)",
            descripcion="Descuenta el cupo usado de la provincia.",
            ejecutar=liberar_cupo,
            campo_estado="estado_cupo",
            motivo_obligatorio=True,
            destructiva=True,
            en_lote=False,
            icono="person_remove",
        ),
    )


@admin.register(AsignacionTecnico)
class AsignacionTecnicoAdmin(SisocModelAdmin):
    list_display = ("expediente", "tecnico", "fecha_asignacion")
    list_select_related = ("expediente__usuario_provincia", "tecnico")
    list_filter = (("fecha_asignacion", RangeDateTimeFilter),)
    search_fields = ("=expediente__id", "tecnico__username")


@admin.register(ExpedienteEstadoHistorial)
class ExpedienteEstadoHistorialAdmin(SoloLecturaAdminMixin, SisocModelAdmin):
    list_display = (
        "expediente",
        "estado_anterior",
        "estado_nuevo",
        "usuario",
        "fecha",
    )
    list_select_related = (
        "expediente__usuario_provincia",
        "estado_anterior",
        "estado_nuevo",
        "usuario",
    )
    list_filter = (
        ("expediente__numero_expediente", FieldTextFilter),
        ("estado_nuevo", RelatedDropdownFilter),
        ("fecha", RangeDateTimeFilter),
    )
    search_fields = ("=expediente__id", "expediente__numero_expediente")


@admin.register(HistorialComentarios)
class HistorialComentariosAdmin(SisocModelAdmin):
    list_display = (
        "legajo",
        "tipo_comentario",
        "comentario_truncado",
        "usuario",
        "fecha_creacion",
    )
    list_select_related = ("legajo__ciudadano", "usuario")
    list_filter = ("tipo_comentario", "fecha_creacion", "usuario")
    search_fields = ("legajo__ciudadano__documento", "comentario")
    readonly_fields = ("fecha_creacion",)

    def comentario_truncado(self, obj):
        return (
            obj.comentario[:50] + "..." if len(obj.comentario) > 50 else obj.comentario
        )

    comentario_truncado.short_description = "Comentario"


@admin.register(TipoDocumento)
class TipoDocumentoAdmin(SisocModelAdmin):
    list_display = ("nombre", "requerido", "orden", "activo")
    list_filter = ("requerido", "activo")
    search_fields = ("nombre", "descripcion")
    ordering = ("orden", "nombre")


class DocumentoLegajoInline(SisocTabularInline):
    model = DocumentoLegajo
    extra = 0
    readonly_fields = ("fecha_carga",)


@admin.register(DocumentoLegajo)
class DocumentoLegajoAdmin(SisocModelAdmin):
    list_display = ("legajo", "tipo_documento", "fecha_carga", "usuario_carga")
    list_select_related = ("legajo__ciudadano", "tipo_documento", "usuario_carga")
    list_filter = ("tipo_documento", "fecha_carga")
    search_fields = ("legajo__ciudadano__documento", "tipo_documento__nombre")
    readonly_fields = ("fecha_carga",)


# Tablas de consulta: el estado lo mueven los services de revisión, cupo,
# RENAPER, subsanación y pago. Se buscan por documento o expediente.
BUSQUEDA_POR_LEGAJO = (
    "=legajo__id",
    "legajo__ciudadano__documento",
    "legajo__ciudadano__apellido",
    "=legajo__expediente__id",
)


@admin.register(ValidacionRenaper)
class ValidacionRenaperAdmin(SoloLecturaAdminMixin, SisocModelAdmin):
    list_display = ("legajo", "estado_validacion", "modificado_en")
    list_select_related = ("legajo__ciudadano",)
    list_filter = (
        ("estado_validacion", ChoicesDropdownFilter),
        ("modificado_en", RangeDateTimeFilter),
    )
    search_fields = BUSQUEDA_POR_LEGAJO


@admin.register(CupoTitular)
class CupoTitularAdmin(SoloLecturaAdminMixin, SisocModelAdmin):
    list_display = ("legajo", "estado_cupo", "es_titular_activo", "modificado_en")
    list_select_related = ("legajo__ciudadano",)
    list_filter = (
        ("estado_cupo", ChoicesDropdownFilter),
        "es_titular_activo",
        ("modificado_en", RangeDateTimeFilter),
    )
    search_fields = BUSQUEDA_POR_LEGAJO


@admin.register(HistorialCupo)
class HistorialCupoAdmin(SoloLecturaAdminMixin, SisocModelAdmin):
    list_display = (
        "legajo",
        "tipo_movimiento",
        "estado_cupo_anterior",
        "estado_cupo_nuevo",
        "es_titular_activo_nuevo",
        "usuario",
        "creado_en",
    )
    list_select_related = ("legajo__ciudadano", "usuario")
    list_filter = (
        ("tipo_movimiento", ChoicesDropdownFilter),
        ("estado_cupo_nuevo", ChoicesDropdownFilter),
        ("creado_en", RangeDateTimeFilter),
    )
    search_fields = BUSQUEDA_POR_LEGAJO


@admin.register(HistorialValidacionTecnica)
class HistorialValidacionTecnicaAdmin(SoloLecturaAdminMixin, SisocModelAdmin):
    list_display = ("legajo", "estado_anterior", "estado_nuevo", "usuario", "creado_en")
    list_select_related = ("legajo__ciudadano", "usuario")
    list_filter = (
        ("estado_nuevo", ChoicesDropdownFilter),
        ("creado_en", RangeDateTimeFilter),
    )
    search_fields = BUSQUEDA_POR_LEGAJO


@admin.register(Subsanacion)
class SubsanacionAdmin(SoloLecturaAdminMixin, SisocModelAdmin):
    list_display = (
        "id",
        "legajo",
        "estado",
        "solicitada_por",
        "solicitada_en",
        "respondida_en",
    )
    list_select_related = ("legajo__ciudadano", "solicitada_por")
    list_filter = (
        ("estado", ChoicesDropdownFilter),
        ("solicitada_en", RangeDateTimeFilter),
        ("respondida_en", RangeDateTimeFilter),
    )
    search_fields = BUSQUEDA_POR_LEGAJO


@admin.register(RegistroErroneo)
class RegistroErroneoAdmin(SoloLecturaAdminMixin, SisocModelAdmin):
    list_display = (
        "id",
        "expediente",
        "fila_excel",
        "campo_error",
        "procesado",
        "creado_en",
    )
    list_select_related = ("expediente__usuario_provincia",)
    list_filter = ("procesado", ("creado_en", RangeDateTimeFilter))
    search_fields = (
        "=expediente__id",
        "expediente__numero_expediente",
        "mensaje_error",
    )


@admin.register(ProvinciaCupo)
class ProvinciaCupoAdmin(SoloLecturaAdminMixin, SisocModelAdmin):
    list_display = ("provincia", "total_asignado", "usados")
    list_select_related = ("provincia",)
    search_fields = ("provincia__nombre",)


@admin.register(CupoMovimiento)
class CupoMovimientoAdmin(SoloLecturaAdminMixin, SisocModelAdmin):
    list_display = (
        "provincia",
        "tipo",
        "delta",
        "legajo",
        "expediente",
        "usuario",
        "creado_en",
    )
    list_select_related = (
        "provincia",
        "legajo__ciudadano",
        "expediente__usuario_provincia",
        "usuario",
    )
    list_filter = (
        ("tipo", ChoicesDropdownFilter),
        ("provincia", RelatedDropdownFilter),
        ("creado_en", RangeDateTimeFilter),
    )
    search_fields = BUSQUEDA_POR_LEGAJO + ("=expediente__id",)


@admin.register(PagoExpediente)
class PagoExpedienteAdmin(SoloLecturaAdminMixin, SisocModelAdmin):
    list_display = (
        "id",
        "provincia",
        "periodo",
        "estado",
        "total_candidatos",
        "total_validados",
        "total_excluidos",
        "creado_en",
    )
    list_select_related = ("provincia",)
    list_filter = (
        ("estado", ChoicesDropdownFilter),
        ("provincia", RelatedDropdownFilter),
        ("creado_en", RangeDateTimeFilter),
    )
    search_fields = ("=id", "periodo", "provincia__nombre")


@admin.register(PagoNomina)
class PagoNominaAdmin(SoloLecturaAdminMixin, SisocModelAdmin):
    list_display = ("pago", "documento", "apellido", "nombre", "estado", "creado_en")
    list_select_related = ("pago__provincia",)
    list_filter = (
        ("estado", ChoicesDropdownFilter),
        ("creado_en", RangeDateTimeFilter),
    )
    search_fields = ("documento", "apellido", "=pago__id", "=legajo__id")
