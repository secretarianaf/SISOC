from django.contrib import admin

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


class OpcionPreguntaInline(ProteccionAprobacionMixin, admin.TabularInline):
    ruta_estado = "encuesta__estado"
    model = OpcionPregunta
    extra = 1


class PreguntaInline(ProteccionAprobacionMixin, admin.TabularInline):
    model = Pregunta
    extra = 1
    fk_name = "encuesta"
    fields = ("texto", "tipo", "obligatoria", "orden")


@admin.register(Encuesta)
class EncuestaAdmin(ProteccionAprobacionMixin, admin.ModelAdmin):
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
    list_filter = ("estado", "es_anonima", "es_obligatoria", "es_recurrente")
    search_fields = ("titulo",)
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
class PreguntaAdmin(ProteccionAprobacionMixin, admin.ModelAdmin):
    ruta_estado = "encuesta__estado"
    list_display = ("texto", "encuesta", "tipo", "obligatoria", "orden")
    list_filter = ("tipo", "obligatoria")
    search_fields = ("texto",)
    inlines = [OpcionPreguntaInline]


@admin.register(SegmentacionEncuesta)
class SegmentacionEncuestaAdmin(ProteccionAprobacionMixin, admin.ModelAdmin):
    ruta_estado = "encuesta__estado"
    list_display = ("encuesta", "tipo")
    list_filter = ("tipo",)


@admin.register(SegmentacionDestinatario)
class SegmentacionDestinatarioAdmin(ProteccionAprobacionMixin, admin.ModelAdmin):
    ruta_estado = "segmentacion__encuesta__estado"
    list_display = ("segmentacion", "tipo_documento", "numero_documento")
    list_filter = ("tipo_documento",)
    search_fields = ("numero_documento",)


@admin.register(RondaEncuesta)
class RondaEncuestaAdmin(admin.ModelAdmin):
    list_display = (
        "encuesta",
        "numero_ronda",
        "estado",
        "fecha_apertura",
        "fecha_cierre_programada",
        "fecha_cierre_real",
    )
    list_filter = ("estado", "cerrada_manualmente")


@admin.register(RespuestaRonda)
class RespuestaRondaAdmin(admin.ModelAdmin):
    list_display = ("ronda", "usuario", "completa", "fecha_respuesta")
    list_filter = ("completa",)


@admin.register(CumplimientoRonda)
class CumplimientoRondaAdmin(admin.ModelAdmin):
    list_display = ("ronda", "usuario")


@admin.register(RespuestaPregunta)
class RespuestaPreguntaAdmin(admin.ModelAdmin):
    list_display = ("respuesta_ronda", "pregunta")


@admin.register(RecordatorioUsuario)
class RecordatorioUsuarioAdmin(admin.ModelAdmin):
    list_display = ("ronda", "usuario", "fecha_proximo_aviso")
