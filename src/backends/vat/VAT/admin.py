from django import forms
from django.contrib import admin
from django.core.exceptions import ValidationError
from unfold.contrib.filters.admin import (
    ChoicesDropdownFilter,
    RangeDateFilter,
    RangeDateTimeFilter,
)

from core.admin_base import SisocModelAdmin, SisocTabularInline
from core.admin_operaciones import Operacion, OperacionesAdminMixin
from VAT.services.inscripcion_service import InscripcionService
from VAT.services.voucher_service.impl import VoucherService
from .models import (
    Centro,
    ModalidadInstitucional,
    Sector,
    Subsector,
    TituloReferencia,
    ModalidadCursada,
    PlanVersionCurricular,
    InscripcionOferta,
    Voucher,
    VoucherRecarga,
    VoucherUso,
    VoucherLog,
    # Fase 2
    InstitucionContacto,
    InstitucionIdentificadorHist,
    InstitucionUbicacion,
    Curso,
    ComisionCurso,
    # Fase 4
    OfertaInstitucional,
    Comision,
    ComisionHorario,
    SesionComision,
    # Fase 5
    Inscripcion,
    SolicitudInscripcionPublica,
    # Fase 6
    AsistenciaSesion,
    # Fase 7
    Evaluacion,
    ResultadoEvaluacion,
    ActaCierreComision,
)


# FKs a tablas grandes con ``raw_id_fields`` y no ``autocomplete_fields``: el
# autocomplete pide ``/admin/autocomplete/``, que atiende el core y no conoce
# los modelos de VAT cuando cada backend corre en su runtime.


# ============================================================================
# OPERACIONES DE SOPORTE (issue #2789)
# ============================================================================
# Cada adaptador llama al service que usa la pantalla equivalente del
# backoffice (views/curso.py, views/oferta_institucional.py, views/voucher.py)
# con el superusuario del admin como actor.


def cambiar_estado_inscripcion(inscripcion, usuario, datos):
    # El service valida cupo, lista de espera y mueve el voucher; un ValueError
    # (estado inválido, cupo completo) queda como error de la fila.
    if inscripcion.estado == datos["nuevo_estado"]:
        raise ValidationError("La inscripción ya tiene ese estado.")
    InscripcionService.actualizar_estado_inscripcion(
        inscripcion=inscripcion,
        nuevo_estado=datos["nuevo_estado"],
        usuario=usuario,
    )


def cancelar_voucher(voucher, usuario, _datos):
    if not VoucherService.cancelar_voucher(voucher=voucher, usuario=usuario):
        raise ValidationError("El voucher ya estaba cancelado.")


def recargar_voucher(voucher, usuario, datos):
    # ``motivo`` del service es el tipo de recarga (VoucherRecarga.MOTIVO_CHOICES);
    # el motivo libre del form queda en la auditoría de la operación.
    ok, mensaje = VoucherService.recargar_voucher(
        voucher=voucher,
        cantidad=datos["cantidad"],
        motivo=datos["tipo_recarga"],
        usuario=usuario,
    )
    if not ok:
        raise ValidationError(mensaje)


OPERACION_CAMBIAR_ESTADO_INSCRIPCION = Operacion(
    slug="cambiar_estado",
    titulo="Cambiar estado de la inscripción",
    descripcion=(
        "Usa la misma regla que el backoffice: controla cupo y lista de espera "
        "y debita o reintegra el voucher cuando corresponde."
    ),
    ejecutar=cambiar_estado_inscripcion,
    campo_estado="estado",
    campos=lambda: {
        "nuevo_estado": forms.ChoiceField(
            label="Nuevo estado", choices=Inscripcion.ESTADO_INSCRIPCION_CHOICES
        )
    },
    icono="swap_horiz",
)

OPERACION_CANCELAR_VOUCHER = Operacion(
    slug="cancelar",
    titulo="Cancelar voucher",
    descripcion="Irreversible: un voucher cancelado no se puede recargar ni usar.",
    ejecutar=cancelar_voucher,
    campo_estado="estado",
    motivo_obligatorio=True,
    destructiva=True,
    icono="block",
)

OPERACION_RECARGAR_VOUCHER = Operacion(
    slug="recargar",
    titulo="Recargar voucher",
    descripcion="Suma créditos al saldo disponible y reactiva el voucher agotado o vencido.",
    ejecutar=recargar_voucher,
    campo_estado="cantidad_disponible",
    motivo_obligatorio=True,
    campos=lambda: {
        "cantidad": forms.IntegerField(label="Créditos a sumar", min_value=1),
        "tipo_recarga": forms.ChoiceField(
            label="Tipo de recarga",
            choices=VoucherRecarga.MOTIVO_CHOICES,
            initial="manual",
        ),
    },
    en_lote=False,
    icono="add_card",
)


@admin.register(Centro)
class CentroAdmin(SisocModelAdmin):
    list_display = ("nombre", "codigo", "tipo_gestion", "activo")
    list_filter = ("activo", "tipo_gestion")
    search_fields = ("nombre", "codigo")
    fieldsets = (
        (
            "Información General",
            {"fields": ("nombre", "codigo", "referente", "referentes", "revisores")},
        ),
        (
            "Ubicación",
            {
                "fields": (
                    "provincia",
                    "municipio",
                    "localidad",
                    "calle",
                    "numero",
                    "domicilio_actividad",
                )
            },
        ),
        ("Contacto", {"fields": ("telefono", "celular", "correo", "sitio_web")}),
        (
            "Responsable",
            {
                "fields": (
                    "nombre_referente",
                    "apellido_referente",
                    "telefono_referente",
                    "correo_referente",
                )
            },
        ),
        (
            "Clasificación",
            {"fields": ("tipo_gestion", "clase_institucion", "situacion")},
        ),
        ("Estado", {"fields": ("activo",)}),
    )


@admin.register(ModalidadInstitucional)
class ModalidadInstitucionalAdmin(SisocModelAdmin):
    list_display = ("nombre", "activo", "fecha_creacion")
    list_filter = ("activo", ("fecha_creacion", RangeDateTimeFilter))
    search_fields = ("nombre",)
    readonly_fields = ("fecha_creacion", "fecha_modificacion")


@admin.register(Sector)
class SectorAdmin(SisocModelAdmin):
    list_display = ("nombre",)
    search_fields = ("nombre",)
    inlines = []


class SubsectorInline(SisocTabularInline):
    model = Subsector
    extra = 1


@admin.register(Subsector)
class SubsectorAdmin(SisocModelAdmin):
    list_display = ("nombre", "sector")
    list_filter = ("sector",)
    list_select_related = ("sector",)
    search_fields = ("nombre",)


@admin.register(TituloReferencia)
class TituloReferenciaAdmin(SisocModelAdmin):
    list_display = ("nombre", "plan_estudio", "activo")
    list_filter = ("plan_estudio", "activo")
    list_select_related = ("plan_estudio",)
    search_fields = (
        "nombre",
        "codigo_referencia",
        "plan_estudio__sector__nombre",
        "plan_estudio__subsector__nombre",
    )
    fieldsets = (
        (
            "Información General",
            {"fields": ("nombre", "codigo_referencia", "descripcion")},
        ),
        ("Clasificación", {"fields": ("plan_estudio",)}),
        ("Estado", {"fields": ("activo",)}),
    )


@admin.register(ModalidadCursada)
class ModalidadCursadaAdmin(SisocModelAdmin):
    list_display = ("nombre", "activo")
    list_filter = ("activo",)
    search_fields = ("nombre",)


@admin.register(PlanVersionCurricular)
class PlanVersionCurricularAdmin(SisocModelAdmin):
    list_display = (
        "sector",
        "subsector",
        "modalidad_cursada",
        "activo",
    )
    list_filter = ("sector", "subsector", "modalidad_cursada", "activo")
    list_select_related = ("sector", "subsector__sector", "modalidad_cursada")
    search_fields = ("sector__nombre", "subsector__nombre", "normativa")
    fieldsets = (
        (
            "Información General",
            {
                "fields": (
                    "sector",
                    "subsector",
                    "modalidad_cursada",
                )
            },
        ),
        ("Normativa y Horas", {"fields": ("normativa", "horas_reloj")}),
        ("Niveles", {"fields": ("nivel_requerido", "nivel_certifica")}),
        ("Estado", {"fields": ("activo",)}),
    )


@admin.register(InscripcionOferta)
class InscripcionOfertaAdmin(SisocModelAdmin):
    list_display = ("ciudadano", "oferta", "estado", "fecha_inscripcion")
    list_filter = (
        ("estado", ChoicesDropdownFilter),
        ("fecha_inscripcion", RangeDateTimeFilter),
    )
    list_select_related = ("ciudadano", "oferta")
    search_fields = ("ciudadano__documento", "ciudadano__nombre", "ciudadano__apellido")
    raw_id_fields = ("ciudadano",)
    readonly_fields = ("fecha_inscripcion", "fecha_modificacion", "inscrito_por")
    fieldsets = (
        ("Información", {"fields": ("oferta", "ciudadano", "estado")}),
        (
            "Auditoría",
            {
                "fields": ("inscrito_por", "fecha_inscripcion", "fecha_modificacion"),
                "classes": ("collapse",),
            },
        ),
    )


@admin.register(Curso)
class CursoAdmin(SisocModelAdmin):
    list_display = (
        "nombre",
        "centro",
        "estado",
        "usa_voucher",
        "inscripcion_libre",
        "prioritario",
    )
    list_filter = ("estado", "centro", "usa_voucher", "inscripcion_libre")
    list_select_related = ("centro",)
    search_fields = ("=id", "nombre", "centro__nombre")
    readonly_fields = ("fecha_creacion", "fecha_modificacion")


@admin.register(ComisionCurso)
class ComisionCursoAdmin(SisocModelAdmin):
    # Sin operaciones: activar, suspender o cerrar una comisión de curso no
    # tiene un service con regla de transición (pendiente, issue #2789).
    list_display = (
        "codigo_comision",
        "nombre",
        "curso",
        "estado",
        "cupo_total",
        "fecha_inicio",
        "fecha_fin",
    )
    list_filter = (
        ("estado", ChoicesDropdownFilter),
        ("fecha_inicio", RangeDateFilter),
        ("fecha_fin", RangeDateFilter),
    )
    list_select_related = ("curso__centro",)
    search_fields = (
        "=id",
        "codigo_comision",
        "nombre",
        "curso__nombre",
        "curso__centro__nombre",
    )
    raw_id_fields = ("curso", "ubicacion")
    readonly_fields = ("fecha_creacion", "fecha_modificacion")


@admin.register(SolicitudInscripcionPublica)
class SolicitudInscripcionPublicaAdmin(SisocModelAdmin):
    list_display = (
        "id",
        "comision_curso",
        "ciudadano",
        "estado",
        "origen_canal",
        "fecha_creacion",
    )
    list_filter = (
        ("estado", ChoicesDropdownFilter),
        "origen_canal",
        "comision_curso__curso__centro",
        ("fecha_creacion", RangeDateTimeFilter),
    )
    list_select_related = ("comision_curso", "ciudadano")
    search_fields = (
        "=id",
        "comision_curso__codigo_comision",
        "ciudadano__documento",
        "ciudadano__apellido",
    )
    raw_id_fields = ("ciudadano", "comision_curso")
    readonly_fields = ("fecha_creacion", "fecha_modificacion")


# ============================================================================
# VOUCHER ADMIN REGISTRATIONS
# ============================================================================


class VoucherRecargaInline(SisocTabularInline):
    model = VoucherRecarga
    extra = 0
    readonly_fields = ("fecha_recarga",)
    fields = ("cantidad", "motivo", "autorizado_por", "fecha_recarga")


class VoucherUsoInline(SisocTabularInline):
    model = VoucherUso
    extra = 0
    readonly_fields = ("fecha_uso",)
    fields = ("inscripcion_oferta", "cantidad_usada", "fecha_uso")


@admin.register(Voucher)
class VoucherAdmin(OperacionesAdminMixin, SisocModelAdmin):
    list_display = (
        "id",
        "ciudadano",
        "cantidad_disponible",
        "cantidad_usada",
        "cantidad_inicial",
        "estado",
        "fecha_vencimiento",
    )
    list_filter = (
        ("estado", ChoicesDropdownFilter),
        "programa",
        ("fecha_vencimiento", RangeDateFilter),
        ("fecha_asignacion", RangeDateFilter),
    )
    list_select_related = ("ciudadano",)
    search_fields = (
        "=id",
        "ciudadano__documento",
        "ciudadano__nombre",
        "ciudadano__apellido",
    )
    raw_id_fields = ("ciudadano",)
    readonly_fields = ("fecha_asignacion", "fecha_creacion", "fecha_modificacion")
    inlines = [VoucherRecargaInline, VoucherUsoInline]
    operaciones = (OPERACION_RECARGAR_VOUCHER, OPERACION_CANCELAR_VOUCHER)
    fieldsets = (
        (
            "Información General",
            {
                "fields": (
                    "ciudadano",
                    "programa",
                    "estado",
                )
            },
        ),
        (
            "Cuotas",
            {
                "fields": (
                    "cantidad_inicial",
                    "cantidad_usada",
                    "cantidad_disponible",
                )
            },
        ),
        (
            "Fechas",
            {
                "fields": (
                    "fecha_asignacion",
                    "fecha_vencimiento",
                )
            },
        ),
        (
            "Auditoría",
            {
                "fields": ("fecha_creacion", "fecha_modificacion"),
                "classes": ("collapse",),
            },
        ),
    )


@admin.register(VoucherRecarga)
class VoucherRecargaAdmin(SisocModelAdmin):
    list_display = ("voucher", "cantidad", "motivo", "fecha_recarga", "autorizado_por")
    list_filter = ("motivo", ("fecha_recarga", RangeDateTimeFilter))
    list_select_related = ("voucher__ciudadano", "autorizado_por")
    search_fields = (
        "voucher__ciudadano__documento",
        "voucher__ciudadano__nombre",
        "voucher__ciudadano__apellido",
    )
    readonly_fields = ("fecha_recarga",)
    fieldsets = (
        ("Información", {"fields": ("voucher", "cantidad", "motivo")}),
        ("Autorización", {"fields": ("autorizado_por",)}),
        ("Auditoría", {"fields": ("fecha_recarga",), "classes": ("collapse",)}),
    )


@admin.register(VoucherUso)
class VoucherUsoAdmin(SisocModelAdmin):
    list_display = ("voucher", "inscripcion_oferta", "cantidad_usada", "fecha_uso")
    list_filter = (("fecha_uso", RangeDateTimeFilter),)
    list_select_related = (
        "voucher__ciudadano",
        "inscripcion_oferta__ciudadano",
        "inscripcion_oferta__oferta",
    )
    search_fields = (
        "voucher__ciudadano__documento",
        "voucher__ciudadano__nombre",
        "voucher__ciudadano__apellido",
    )
    readonly_fields = ("fecha_uso",)
    fieldsets = (
        (
            "Información",
            {"fields": ("voucher", "inscripcion_oferta", "cantidad_usada")},
        ),
        ("Auditoría", {"fields": ("fecha_uso",), "classes": ("collapse",)}),
    )


@admin.register(VoucherLog)
class VoucherLogAdmin(SisocModelAdmin):
    list_display = (
        "voucher",
        "tipo_evento",
        "cantidad_afectada",
        "fecha_evento",
        "usuario",
    )
    list_filter = ("tipo_evento", ("fecha_evento", RangeDateTimeFilter))
    list_select_related = ("voucher__ciudadano", "usuario")
    search_fields = (
        "voucher__ciudadano__documento",
        "voucher__ciudadano__nombre",
        "voucher__ciudadano__apellido",
    )
    readonly_fields = (
        "fecha_evento",
        "voucher",
        "tipo_evento",
        "cantidad_afectada",
        "usuario",
        "detalles",
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    fieldsets = (
        (
            "Evento",
            {
                "fields": (
                    "voucher",
                    "tipo_evento",
                    "cantidad_afectada",
                )
            },
        ),
        (
            "Auditoría",
            {
                "fields": ("usuario", "fecha_evento", "detalles"),
                "classes": ("collapse",),
            },
        ),
    )


# ============================================================================
# FASE 2: INSTITUCIÓN - CONTACTOS E IDENTIFICADORES
# ============================================================================


@admin.register(InstitucionContacto)
class InstitucionContactoAdmin(SisocModelAdmin):
    list_display = (
        "centro",
        "tipo",
        "valor",
        "es_principal",
        "vigencia_desde",
        "vigencia_hasta",
    )
    list_filter = ("tipo", "es_principal", ("vigencia_desde", RangeDateFilter))
    list_select_related = ("centro",)
    search_fields = ("centro__nombre", "valor")
    readonly_fields = ("vigencia_desde", "fecha_creacion", "fecha_modificacion")


@admin.register(InstitucionIdentificadorHist)
class InstitucionIdentificadorHistAdmin(SisocModelAdmin):
    list_display = (
        "centro",
        "tipo_identificador",
        "valor_identificador",
        "rol_institucional",
        "es_actual",
    )
    list_filter = ("tipo_identificador", "rol_institucional", "es_actual")
    list_select_related = ("centro",)
    search_fields = ("centro__nombre", "valor_identificador")
    readonly_fields = ("vigencia_desde", "fecha_creacion", "fecha_modificacion")


@admin.register(InstitucionUbicacion)
class InstitucionUbicacionAdmin(SisocModelAdmin):
    list_display = ("centro", "localidad", "rol_ubicacion", "es_principal", "domicilio")
    list_filter = ("rol_ubicacion", "es_principal")
    list_select_related = ("centro", "localidad")
    search_fields = ("centro__nombre", "localidad__nombre", "domicilio")
    readonly_fields = ("vigencia_desde", "fecha_creacion", "fecha_modificacion")


# ============================================================================
# FASE 4: OFERTA INSTITUCIONAL - COMISIONES
# ============================================================================


class ComisionInline(SisocTabularInline):
    model = Comision
    extra = 0
    readonly_fields = ("fecha_creacion", "fecha_modificacion")


@admin.register(OfertaInstitucional)
class OfertaInstitucionalAdmin(SisocModelAdmin):
    list_display = (
        "centro",
        "plan_curricular",
        "ciclo_lectivo",
        "estado",
        "usa_voucher",
    )
    list_filter = ("estado", "centro", "ciclo_lectivo", "usa_voucher")
    list_select_related = ("centro", "plan_curricular")
    search_fields = ("=id", "centro__nombre", "plan_curricular__titulos__nombre")
    inlines = [ComisionInline]
    readonly_fields = ("fecha_creacion", "fecha_modificacion")
    fieldsets = (
        ("Información", {"fields": ("centro", "plan_curricular", "programa")}),
        ("Detalles", {"fields": ("nombre_local", "ciclo_lectivo", "plan_externo_id")}),
        (
            "Estado y Voucher",
            {"fields": ("estado", "costo", "usa_voucher", "fecha_publicacion")},
        ),
        (
            "Auditoría",
            {
                "fields": ("observaciones", "fecha_creacion", "fecha_modificacion"),
                "classes": ("collapse",),
            },
        ),
    )


class ComisionHorarioInline(SisocTabularInline):
    model = ComisionHorario
    extra = 0
    readonly_fields = ("fecha_creacion", "fecha_modificacion")


@admin.register(Comision)
class ComisionAdmin(SisocModelAdmin):
    list_display = (
        "codigo_comision",
        "nombre",
        "oferta",
        "cupo",
        "estado",
        "fecha_inicio",
    )
    list_filter = ("estado", "oferta__centro", ("fecha_inicio", RangeDateFilter))
    list_select_related = ("oferta__centro", "oferta__plan_curricular")
    search_fields = ("=id", "codigo_comision", "nombre", "oferta__centro__nombre")
    inlines = [ComisionHorarioInline]
    readonly_fields = ("fecha_creacion", "fecha_modificacion")
    fieldsets = (
        (
            "Información",
            {"fields": ("oferta", "ubicacion", "codigo_comision", "nombre")},
        ),
        ("Período", {"fields": ("fecha_inicio", "fecha_fin")}),
        ("Capacidad", {"fields": ("cupo", "estado")}),
        (
            "Auditoría",
            {
                "fields": ("observaciones", "fecha_creacion", "fecha_modificacion"),
                "classes": ("collapse",),
            },
        ),
    )


@admin.register(ComisionHorario)
class ComisionHorarioAdmin(SisocModelAdmin):
    list_display = (
        "comision",
        "comision_curso",
        "dia_semana",
        "hora_desde",
        "hora_hasta",
        "aula_espacio",
        "vigente",
    )
    list_filter = ("vigente", "dia_semana")
    list_select_related = ("comision", "comision_curso", "dia_semana")
    search_fields = (
        "comision__codigo_comision",
        "comision_curso__codigo_comision",
        "aula_espacio",
    )
    readonly_fields = ("fecha_creacion", "fecha_modificacion")


@admin.register(SesionComision)
class SesionComisionAdmin(SisocModelAdmin):
    # Sin operaciones: realizar o cancelar una sesión no tiene un service con
    # regla de transición (pendiente, issue #2789).
    list_display = (
        "id",
        "numero_sesion",
        "fecha",
        "comision",
        "comision_curso",
        "estado",
    )
    list_filter = (("estado", ChoicesDropdownFilter), ("fecha", RangeDateFilter))
    list_select_related = ("comision", "comision_curso")
    search_fields = (
        "=id",
        "comision__codigo_comision",
        "comision_curso__codigo_comision",
    )
    raw_id_fields = ("comision", "comision_curso", "horario")
    readonly_fields = ("fecha_creacion",)


# ============================================================================
# FASE 5: INSCRIPCIÓN
# ============================================================================


@admin.register(Inscripcion)
class InscripcionAdmin(OperacionesAdminMixin, SisocModelAdmin):
    list_display = (
        "id",
        "ciudadano",
        "comision",
        "comision_curso",
        "estado",
        "fecha_inscripcion",
        "programa",
    )
    list_filter = (
        ("estado", ChoicesDropdownFilter),
        "comision__oferta__centro",
        ("fecha_inscripcion", RangeDateTimeFilter),
        "programa",
    )
    list_select_related = ("ciudadano", "comision", "comision_curso", "programa")
    search_fields = (
        "=id",
        "ciudadano__documento",
        "ciudadano__nombre",
        "ciudadano__apellido",
        "comision__codigo_comision",
        "comision_curso__codigo_comision",
    )
    raw_id_fields = ("ciudadano", "comision", "comision_curso")
    readonly_fields = ("fecha_inscripcion", "fecha_creacion", "fecha_modificacion")
    operaciones = (OPERACION_CAMBIAR_ESTADO_INSCRIPCION,)
    fieldsets = (
        (
            "Información",
            {"fields": ("ciudadano", "comision", "comision_curso", "programa")},
        ),
        (
            "Estado",
            {"fields": ("estado", "origen_canal", "fecha_validacion_presencial")},
        ),
        (
            "Auditoría",
            {
                "fields": (
                    "observaciones",
                    "fecha_inscripcion",
                    "fecha_creacion",
                    "fecha_modificacion",
                ),
                "classes": ("collapse",),
            },
        ),
    )


# ============================================================================
# FASE 6: ASISTENCIA
# ============================================================================


@admin.register(AsistenciaSesion)
class AsistenciaSesionAdmin(SisocModelAdmin):
    list_display = (
        "sesion",
        "inscripcion",
        "presente",
        "registrado_por",
        "fecha_registro",
    )
    list_filter = (
        "presente",
        "sesion__comision",
        ("fecha_registro", RangeDateTimeFilter),
    )
    list_select_related = (
        "sesion__comision",
        "sesion__comision_curso",
        "inscripcion__ciudadano",
        "inscripcion__comision",
        "inscripcion__comision_curso",
        "registrado_por",
    )
    search_fields = (
        "inscripcion__ciudadano__documento",
        "inscripcion__ciudadano__nombre",
        "inscripcion__ciudadano__apellido",
        "sesion__comision__codigo_comision",
        "sesion__comision_curso__codigo_comision",
    )
    readonly_fields = ("fecha_registro",)


# ============================================================================
# FASE 7: EVALUACIONES
# ============================================================================


class ResultadoEvaluacionInline(SisocTabularInline):
    model = ResultadoEvaluacion
    extra = 0
    readonly_fields = ("fecha_registro", "fecha_creacion", "fecha_modificacion")
    fields = ("inscripcion", "calificacion", "aprobo", "registrado_por")


@admin.register(Evaluacion)
class EvaluacionAdmin(SisocModelAdmin):
    list_display = ("comision", "nombre", "tipo", "fecha", "es_final", "ponderacion")
    list_filter = (
        "tipo",
        "es_final",
        "comision__oferta__centro",
        ("fecha", RangeDateFilter),
    )
    list_select_related = ("comision",)
    search_fields = ("nombre", "comision__codigo_comision")
    inlines = [ResultadoEvaluacionInline]
    readonly_fields = ("fecha_creacion", "fecha_modificacion")
    fieldsets = (
        ("Información", {"fields": ("comision", "nombre", "tipo", "es_final")}),
        (
            "Detalles",
            {"fields": ("fecha", "descripcion", "ponderacion", "observaciones")},
        ),
        (
            "Auditoría",
            {
                "fields": ("fecha_creacion", "fecha_modificacion"),
                "classes": ("collapse",),
            },
        ),
    )


@admin.register(ResultadoEvaluacion)
class ResultadoEvaluacionAdmin(SisocModelAdmin):
    list_display = (
        "inscripcion",
        "evaluacion",
        "calificacion",
        "aprobo",
        "fecha_registro",
        "registrado_por",
    )
    list_filter = (
        "aprobo",
        "evaluacion__tipo",
        ("fecha_registro", RangeDateTimeFilter),
    )
    list_select_related = (
        "inscripcion__ciudadano",
        "inscripcion__comision",
        "inscripcion__comision_curso",
        "evaluacion__comision",
        "registrado_por",
    )
    search_fields = (
        # Inscripcion no tiene ``persona``: el inscripto es ``ciudadano``.
        "inscripcion__ciudadano__documento",
        "inscripcion__ciudadano__nombre",
        "inscripcion__ciudadano__apellido",
        "evaluacion__nombre",
    )
    readonly_fields = ("fecha_registro", "fecha_creacion", "fecha_modificacion")
    fieldsets = (
        ("Información", {"fields": ("evaluacion", "inscripcion")}),
        ("Resultados", {"fields": ("calificacion", "aprobo", "observaciones")}),
        (
            "Auditoría",
            {
                "fields": (
                    "registrado_por",
                    "fecha_registro",
                    "fecha_creacion",
                    "fecha_modificacion",
                ),
                "classes": ("collapse",),
            },
        ),
    )


@admin.register(ActaCierreComision)
class ActaCierreComisionAdmin(SisocModelAdmin):
    # Sin operaciones: el acta se carga desde la pantalla de cierre de la
    # comisión (resultados_comision_service), que necesita el form completo.
    list_display = (
        "numero_acta",
        "comision_curso",
        "profesor",
        "fecha_fin",
        "registrado_por",
        "fecha_creacion",
    )
    list_filter = (
        ("fecha_fin", RangeDateFilter),
        ("fecha_creacion", RangeDateTimeFilter),
    )
    list_select_related = ("comision_curso", "profesor", "registrado_por")
    search_fields = (
        "=id",
        "numero_acta",
        "comision_curso__codigo_comision",
        "comision_curso__nombre",
        "profesor__documento",
        "profesor__apellido",
    )
    raw_id_fields = ("comision_curso", "profesor", "registrado_por")
    readonly_fields = ("fecha_creacion", "fecha_modificacion")
