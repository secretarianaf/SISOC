from django.contrib import admin
from unfold.contrib.filters.admin import (
    ChoicesDropdownFilter,
    RangeDateFilter,
    RangeDateTimeFilter,
    RelatedDropdownFilter,
)

from core.admin_base import SisocModelAdmin
from core.admin_operaciones import Operacion, OperacionesAdminMixin
from centrodeinfancia.forms import NominaCentroInfanciaAdminForm
from centrodeinfancia.models import (
    AccesoCDI,
    AsistenciaNominaCentroInfancia,
    CentroDeInfancia,
    DepartamentoIpi,
    FormularioCDI,
    FormularioCDIArticulationFrequency,
    FormularioCDIRoomDistribution,
    FormularioCDIWaitlistByAgeGroup,
    IntervencionCentroInfancia,
    NominaCentroInfancia,
    NominaCentroInfanciaDerivacion,
    ObservacionCentroInfancia,
    OfertaServicio,
    Trabajador,
)
from centrodeinfancia.services_accesos_cdi import (
    ACCION_BAJA,
    ACCION_REACTIVAR,
    ACCION_SUSPENDER,
    cambiar_estado_acceso,
)


# Operaciones de soporte (issue #2789): las transiciones, el motivo obligatorio
# y los bloqueos (propio usuario, responsable) los aplica cambiar_estado_acceso,
# igual que la botonera "Usuarios del centro" (cambiar_estado_usuario_cdi).


def _cambiar_estado(acceso, usuario, accion, datos):
    return cambiar_estado_acceso(
        actor=usuario, acceso=acceso, accion=accion, motivo=datos.get("motivo", "")
    )


def suspender_acceso(acceso, usuario, datos):
    return _cambiar_estado(acceso, usuario, ACCION_SUSPENDER, datos)


def reactivar_acceso(acceso, usuario, datos):
    return _cambiar_estado(acceso, usuario, ACCION_REACTIVAR, datos)


def dar_de_baja_acceso(acceso, usuario, datos):
    return _cambiar_estado(acceso, usuario, ACCION_BAJA, datos)


@admin.register(CentroDeInfancia)
class CentroDeInfanciaAdmin(SisocModelAdmin):
    list_display = (
        "id",
        "nombre",
        "organizacion",
        "provincia",
        "departamento",
        "fecha_creacion",
    )
    list_select_related = ("provincia", "departamento")
    list_filter = (
        ("provincia", RelatedDropdownFilter),
        ("fecha_creacion", RangeDateTimeFilter),
    )
    search_fields = (
        "=id",
        "nombre",
        "organizacion",
        "cuit_organizacion_gestiona",
        "provincia__nombre",
        "departamento__nombre",
    )


@admin.register(DepartamentoIpi)
class DepartamentoIpiAdmin(SisocModelAdmin):
    list_display = (
        "codigo_departamento",
        "nombre",
        "provincia",
        "decil_ipi",
        "nivel_inequidad_ipi",
    )
    list_select_related = ("provincia",)
    list_filter = ("provincia", "nivel_inequidad_ipi")
    search_fields = ("codigo_departamento", "nombre", "provincia__nombre")


@admin.register(NominaCentroInfancia)
class NominaCentroInfanciaAdmin(SisocModelAdmin):
    form = NominaCentroInfanciaAdminForm
    list_display = ("id", "centro", "ciudadano", "dni", "estado", "fecha")
    list_select_related = ("centro", "ciudadano")
    list_filter = (
        ("estado", ChoicesDropdownFilter),
        ("fecha", RangeDateTimeFilter),
    )
    search_fields = (
        "=id",
        "dni",
        "ciudadano__documento",
        "centro__nombre",
        "ciudadano__apellido",
        "ciudadano__nombre",
    )
    raw_id_fields = ("centro", "ciudadano")


@admin.register(AsistenciaNominaCentroInfancia)
class AsistenciaNominaCentroInfanciaAdmin(SisocModelAdmin):
    list_display = ("id", "nomina", "fecha", "presente", "registrado_por")
    list_filter = (("fecha", RangeDateFilter), "presente")
    search_fields = (
        "nomina__ciudadano__documento",
        "nomina__centro__nombre",
        "nomina__ciudadano__apellido",
        "nomina__ciudadano__nombre",
    )
    # ``str(nomina)`` muestra ciudadano y centro.
    list_select_related = ("nomina__ciudadano", "nomina__centro", "registrado_por")


@admin.register(Trabajador)
class TrabajadorAdmin(SisocModelAdmin):
    list_display = ("id", "centro", "apellido", "nombre", "dni", "rol", "telefono")
    list_select_related = ("centro",)
    list_filter = ("rol",)
    search_fields = ("dni", "centro__nombre", "apellido", "nombre", "telefono")
    raw_id_fields = ("usuario", "centro")


@admin.register(IntervencionCentroInfancia)
class IntervencionCentroInfanciaAdmin(SisocModelAdmin):
    list_display = ("id", "centro", "tipo_intervencion", "fecha")
    list_select_related = ("centro", "tipo_intervencion")
    list_filter = ("tipo_intervencion", "destinatario")
    search_fields = ("centro__nombre", "observaciones")


@admin.register(ObservacionCentroInfancia)
class ObservacionCentroInfanciaAdmin(SisocModelAdmin):
    list_display = ("id", "centro", "observador", "fecha_visita")
    list_select_related = ("centro",)
    list_filter = (("fecha_visita", RangeDateTimeFilter),)
    search_fields = ("centro__nombre", "observador", "observacion")


@admin.register(FormularioCDI)
class FormularioCDIAdmin(SisocModelAdmin):
    list_display = (
        "id",
        "centro",
        "fecha_relevamiento",
        "nombre_completo_respondente",
        "created_at",
    )
    list_select_related = ("centro",)
    list_filter = (
        ("fecha_relevamiento", RangeDateFilter),
        ("created_at", RangeDateTimeFilter),
    )
    search_fields = ("centro__nombre", "nombre_completo_respondente", "codigo_cdi")


# ``str(formulario)`` muestra el centro.
@admin.register(FormularioCDIRoomDistribution)
class FormularioCDIRoomDistributionAdmin(SisocModelAdmin):
    list_display = (
        "id",
        "formulario",
        "grupo_etario",
        "cantidad_salas",
        "cantidad_ninos",
    )
    list_select_related = ("formulario__centro",)
    list_filter = ("grupo_etario",)


@admin.register(FormularioCDIWaitlistByAgeGroup)
class FormularioCDIWaitlistByAgeGroupAdmin(SisocModelAdmin):
    list_display = ("id", "formulario", "grupo_etario", "cantidad_demanda_insatisfecha")
    list_select_related = ("formulario__centro",)
    list_filter = ("grupo_etario",)


@admin.register(FormularioCDIArticulationFrequency)
class FormularioCDIArticulationFrequencyAdmin(SisocModelAdmin):
    list_display = ("id", "formulario", "tipo_institucion", "frecuencia")
    list_select_related = ("formulario__centro",)
    list_filter = ("frecuencia",)


@admin.register(NominaCentroInfanciaDerivacion)
class NominaCentroInfanciaDerivacionAdmin(SisocModelAdmin):
    list_display = (
        "id",
        "nomina_origen",
        "nomina_destino",
        "centro_origen",
        "centro_destino",
        "usuario",
        "fecha",
    )
    # ``str(nomina)`` muestra ciudadano y centro.
    list_select_related = (
        "nomina_origen__ciudadano",
        "nomina_origen__centro",
        "nomina_destino__ciudadano",
        "nomina_destino__centro",
        "centro_origen",
        "centro_destino",
        "usuario",
    )
    list_filter = (("fecha", RangeDateTimeFilter),)
    search_fields = (
        "nomina_origen__ciudadano__documento",
        "usuario__username",
        "centro_origen__nombre",
        "centro_destino__nombre",
    )
    readonly_fields = (
        "nomina_origen",
        "nomina_destino",
        "centro_origen",
        "centro_destino",
        "usuario",
        "fecha",
        "motivo",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(AccesoCDI)
class AccesoCDIAdmin(OperacionesAdminMixin, SisocModelAdmin):
    list_display = ("user", "centro", "estado", "es_responsable", "fecha_creacion")
    list_select_related = ("user", "centro")
    list_filter = (
        ("estado", ChoicesDropdownFilter),
        "es_responsable",
        ("fecha_creacion", RangeDateTimeFilter),
    )
    search_fields = ("user__username", "user__email", "centro__nombre")
    raw_id_fields = ("user", "creado_por", "centro")
    # ``activo`` se deriva de ``estado`` al guardar; ``estado`` y su motivo solo
    # cambian por las operaciones.
    readonly_fields = ("activo", "motivo_estado", "fecha_creacion", "fecha_baja")
    operaciones = (
        Operacion(
            slug="suspender",
            titulo="Suspender acceso",
            ejecutar=suspender_acceso,
            campo_estado="estado",
            motivo_obligatorio=True,
            icono="pause_circle",
        ),
        Operacion(
            slug="reactivar",
            titulo="Reactivar acceso",
            ejecutar=reactivar_acceso,
            campo_estado="estado",
            icono="play_circle",
        ),
        Operacion(
            slug="dar_de_baja",
            titulo="Dar de baja el acceso",
            descripcion="La baja es definitiva para este CDI y libera el cupo.",
            ejecutar=dar_de_baja_acceso,
            campo_estado="estado",
            motivo_obligatorio=True,
            destructiva=True,
            icono="person_remove",
        ),
    )


@admin.register(OfertaServicio)
class OfertaServicioAdmin(SisocModelAdmin):
    list_display = ("codigo", "orden")
    search_fields = ("codigo",)
