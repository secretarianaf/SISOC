from django.contrib import admin
from unfold.contrib.filters.admin import ChoicesDropdownFilter, RangeDateTimeFilter

from core.admin_base import SisocModelAdmin, SisocTabularInline
from core.admin_operaciones import Operacion, OperacionesAdminMixin
from .services import (
    cerrar_ronda,
    publicar,
    rechazar_publicacion,
    solicitar_publicacion,
)
from .models import (
    CumplimientoRonda,
    Encuesta,
    EstadoEncuesta,
    OpcionPregunta,
    Pregunta,
    RecordatorioUsuario,
    RespuestaPregunta,
    RespuestaRonda,
    RondaEncuesta,
    SegmentacionDestinatario,
    SegmentacionEncuesta,
)


class ProteccionAprobacionMixin:
    """Mantiene inmutable el contenido pendiente también en Django admin."""

    ruta_estado = "estado"

    def _pendiente(self, obj):
        return (
            obj is not None
            and type(obj)
            .objects.filter(
                pk=obj.pk, **{self.ruta_estado: EstadoEncuesta.PENDIENTE_APROBACION}
            )
            .exists()
        )

    def has_change_permission(self, request, obj=None):
        return not self._pendiente(obj) and super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        return not self._pendiente(obj) and super().has_delete_permission(request, obj)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        rutas = {
            "encuesta": "estado",
            "pregunta": "encuesta__estado",
            "segmentacion": "encuesta__estado",
        }
        if db_field.name in rutas:
            kwargs["queryset"] = db_field.remote_field.model.objects.exclude(
                **{rutas[db_field.name]: EstadoEncuesta.PENDIENTE_APROBACION}
            )
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


class OpcionPreguntaInline(ProteccionAprobacionMixin, SisocTabularInline):
    ruta_estado = "encuesta__estado"
    model = OpcionPregunta
    extra = 1


class PreguntaInline(ProteccionAprobacionMixin, SisocTabularInline):
    model = Pregunta
    extra = 1
    fk_name = "encuesta"
    fields = ("texto", "tipo", "obligatoria", "orden")


def _solicitar_publicacion(encuesta, usuario, _datos):
    solicitar_publicacion(encuesta, usuario=usuario)


def _publicar(encuesta, usuario, _datos):
    publicar(encuesta, usuario=usuario)


def _rechazar_publicacion(encuesta, usuario, datos):
    rechazar_publicacion(encuesta, usuario=usuario, motivo=datos["motivo"])


def _cerrar_ronda(ronda, _usuario, _datos):
    cerrar_ronda(ronda, manual=True)


# Mismas transiciones que las vistas de encuestas (EncuestaPublicarView,
# EncuestaAprobarView, EncuestaRechazarView): el service valida el estado.
@admin.register(Encuesta)
class EncuestaAdmin(OperacionesAdminMixin, ProteccionAprobacionMixin, SisocModelAdmin):
    operaciones = (
        Operacion(
            slug="solicitar_publicacion",
            titulo="Solicitar publicación",
            descripcion="Pasa la encuesta de borrador a pendiente de aprobación.",
            ejecutar=_solicitar_publicacion,
            campo_estado="estado",
            icono="send",
        ),
        Operacion(
            slug="publicar",
            titulo="Aprobar y publicar",
            descripcion=(
                "Publica una encuesta pendiente de aprobación y abre su primera ronda."
            ),
            ejecutar=_publicar,
            campo_estado="estado",
            icono="publish",
        ),
        Operacion(
            slug="rechazar_publicacion",
            titulo="Rechazar publicación",
            descripcion=(
                "Devuelve la encuesta a borrador. El motivo le llega al gestor como "
                "lo que debe corregir."
            ),
            ejecutar=_rechazar_publicacion,
            campo_estado="estado",
            motivo_obligatorio=True,
            icono="undo",
        ),
    )
    list_display = (
        "titulo",
        "version",
        "estado",
        "es_anonima",
        "es_obligatoria",
        "es_recurrente",
        "usuario_creador",
        "fecha_creacion",
    )
    list_filter = (
        ("estado", ChoicesDropdownFilter),
        "es_anonima",
        "es_obligatoria",
        "es_recurrente",
        ("fecha_creacion", RangeDateTimeFilter),
    )
    search_fields = ("titulo", "usuario_creador__username")
    list_select_related = ("usuario_creador",)
    readonly_fields = (
        "estado",
        "usuario_creador",
        "usuario_ultima_modificacion",
        "motivo_rechazo",
        "usuario_rechazo",
        "fecha_rechazo",
    )
    inlines = [PreguntaInline]


@admin.register(Pregunta)
class PreguntaAdmin(ProteccionAprobacionMixin, SisocModelAdmin):
    ruta_estado = "encuesta__estado"
    list_display = ("texto", "encuesta", "tipo", "obligatoria", "orden")
    list_filter = ("tipo", "obligatoria")
    search_fields = ("texto", "encuesta__titulo")
    list_select_related = ("encuesta",)
    inlines = [OpcionPreguntaInline]


@admin.register(SegmentacionEncuesta)
class SegmentacionEncuestaAdmin(ProteccionAprobacionMixin, SisocModelAdmin):
    ruta_estado = "encuesta__estado"
    list_display = ("encuesta", "tipo")
    list_filter = ("tipo",)
    search_fields = ("encuesta__titulo",)
    list_select_related = ("encuesta",)


@admin.register(SegmentacionDestinatario)
class SegmentacionDestinatarioAdmin(ProteccionAprobacionMixin, SisocModelAdmin):
    ruta_estado = "segmentacion__encuesta__estado"
    list_display = ("segmentacion", "tipo_documento", "numero_documento")
    list_filter = ("tipo_documento",)
    search_fields = ("numero_documento",)
    list_select_related = ("segmentacion__encuesta",)


@admin.register(RondaEncuesta)
class RondaEncuestaAdmin(OperacionesAdminMixin, SisocModelAdmin):
    operaciones = (
        Operacion(
            slug="cerrar",
            titulo="Cerrar ronda",
            descripcion=(
                "Cierra la ronda abierta antes de la fecha programada. No se puede "
                "reabrir."
            ),
            ejecutar=_cerrar_ronda,
            campo_estado="estado",
            destructiva=True,
            icono="lock",
        ),
    )
    list_display = (
        "encuesta",
        "numero_ronda",
        "estado",
        "fecha_apertura",
        "fecha_cierre_programada",
        "fecha_cierre_real",
    )
    list_filter = (
        ("estado", ChoicesDropdownFilter),
        "cerrada_manualmente",
        ("fecha_apertura", RangeDateTimeFilter),
        ("fecha_cierre_real", RangeDateTimeFilter),
    )
    search_fields = ("encuesta__titulo",)
    list_select_related = ("encuesta",)


@admin.register(RespuestaRonda)
class RespuestaRondaAdmin(SisocModelAdmin):
    list_display = ("ronda", "usuario", "completa", "fecha_respuesta")
    list_filter = ("completa", ("fecha_respuesta", RangeDateTimeFilter))
    search_fields = ("usuario__username", "ronda__encuesta__titulo")
    list_select_related = ("ronda__encuesta", "usuario")
    autocomplete_fields = ("ronda", "usuario")


@admin.register(CumplimientoRonda)
class CumplimientoRondaAdmin(SisocModelAdmin):
    list_display = ("ronda", "usuario")
    search_fields = ("usuario__username", "ronda__encuesta__titulo")
    list_select_related = ("ronda__encuesta", "usuario")
    autocomplete_fields = ("ronda", "usuario")


@admin.register(RespuestaPregunta)
class RespuestaPreguntaAdmin(SisocModelAdmin):
    list_display = ("respuesta_ronda", "pregunta")
    search_fields = ("respuesta_ronda__usuario__username", "pregunta__texto")
    list_select_related = (
        "respuesta_ronda__ronda__encuesta",
        "respuesta_ronda__usuario",
        "pregunta",
    )
    raw_id_fields = ("respuesta_ronda", "pregunta")


@admin.register(RecordatorioUsuario)
class RecordatorioUsuarioAdmin(SisocModelAdmin):
    list_display = ("ronda", "usuario", "fecha_proximo_aviso")
    list_filter = (("fecha_proximo_aviso", RangeDateTimeFilter),)
    search_fields = ("usuario__username", "ronda__encuesta__titulo")
    list_select_related = ("ronda__encuesta", "usuario")
    autocomplete_fields = ("ronda", "usuario")
