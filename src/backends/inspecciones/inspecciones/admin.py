"""Admin de Inspecciones escolares.

El catálogo y las asignaciones se editan aquí o se importan desde el panel del
backoffice (``/inspecciones/``). Inspecciones, actas, notificaciones y eventos
son de sólo lectura: el acta es inmutable y su historial es evidencia. Las
correcciones de soporte (anular, marcar prueba, quitar asignación) van por
operaciones que llaman a los services del backoffice (issue #2789).
"""

from django import forms
from django.contrib import admin
from django.core.exceptions import ValidationError
from import_export import resources
from unfold.contrib.filters.admin import (
    ChoicesDropdownFilter,
    RangeDateFilter,
    RangeDateTimeFilter,
)

from core.admin_base import SisocModelAdmin, SoloLecturaAdmin
from core.admin_import_export import BaseImportExportAdmin
from core.admin_operaciones import Operacion, OperacionesAdminMixin
from inspecciones.models import (
    Acta,
    AsignacionEscuela,
    Escuela,
    EventoInspeccion,
    Inspeccion,
    NotificacionPapel,
)
from inspecciones.services.anulacion import MIN_MOTIVO, anular_acta, marcar_prueba
from inspecciones.services.asignaciones import quitar_asignacion

# Mismos valores que manda el backoffice (views_anulacion.VALORES_PRUEBA).
MARCAR_PRUEBA_CHOICES = (("1", "Marcar como prueba"), ("0", "Desmarcar"))


def anular(acta, usuario, datos):
    anular_acta(acta, datos["motivo"], usuario)


def marcar_o_desmarcar_prueba(acta, usuario, datos):
    es_prueba = datos["es_prueba"] == "1"
    if acta.es_prueba == es_prueba:
        raise ValidationError("El acta ya tiene esa marca.")
    marcar_prueba(acta, es_prueba, usuario)


def quitar(asignacion, usuario, _datos):
    # Baja lógica; el service la rechaza si la visita ya tiene acta.
    quitar_asignacion(asignacion, actor=usuario)


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
class AsignacionEscuelaAdmin(OperacionesAdminMixin, SisocModelAdmin):
    list_display = ("fecha", "escuela", "inspector")
    list_filter = (("fecha", RangeDateFilter),)
    list_select_related = ("escuela", "inspector")
    search_fields = ("escuela__nombre", "escuela__cue", "inspector__username")
    raw_id_fields = ("inspector", "escuela")
    operaciones = (
        Operacion(
            slug="quitar",
            titulo="Quitar asignación",
            descripcion=(
                "Baja lógica de la asignación (recuperable desde la papelera). "
                "No se puede si la visita ya tiene acta en esa jornada."
            ),
            ejecutar=quitar,
            campo_estado="deleted_at",
            motivo_obligatorio=True,
            icono="person_remove",
        ),
    )


@admin.register(Inspeccion)
class InspeccionAdmin(SoloLecturaAdmin):
    list_display = ("uuid", "inspector", "estado", "escuela", "fecha_visita", "turno")
    list_filter = (
        ("estado", ChoicesDropdownFilter),
        ("fecha_visita", RangeDateFilter),
        "turno",
    )
    list_select_related = ("inspector", "escuela")
    search_fields = ("uuid", "inspector__username", "escuela__nombre", "escuela__cue")


@admin.register(Acta)
class ActaAdmin(OperacionesAdminMixin, SoloLecturaAdmin):
    list_display = (
        "numero",
        "inspector",
        "escuela",
        "fecha_visita",
        "turno",
        "estado",
        "notificacion_estado",
        "es_prueba",
    )
    list_filter = (
        ("estado", ChoicesDropdownFilter),
        ("notificacion_estado", ChoicesDropdownFilter),
        "es_prueba",
        ("fecha_visita", RangeDateFilter),
        ("cerrada_at", RangeDateTimeFilter),
        "turno",
    )
    list_select_related = ("inspector", "escuela")
    search_fields = ("numero", "inspector__username", "escuela__nombre", "escuela__cue")
    operaciones = (
        Operacion(
            slug="anular",
            titulo="Anular acta",
            descripcion=(
                "Irreversible. Conserva número, instantánea y PDF; la escuela "
                "vuelve a quedar pendiente en la jornada."
            ),
            ejecutar=anular,
            campo_estado="estado",
            motivo_obligatorio=True,
            motivo_min_largo=MIN_MOTIVO,
            destructiva=True,
            icono="block",
        ),
        Operacion(
            slug="marcar_prueba",
            titulo="Marcar o desmarcar como prueba",
            descripcion="Un acta de prueba queda fuera de los indicadores.",
            ejecutar=marcar_o_desmarcar_prueba,
            campo_estado="es_prueba",
            campos=lambda: {
                "es_prueba": forms.ChoiceField(
                    label="Acta de prueba", choices=MARCAR_PRUEBA_CHOICES
                )
            },
            icono="science",
        ),
    )

    def has_change_permission(self, request, obj=None):
        # El acta es inmutable: el detalle (con ``obj``) sigue de sólo lectura,
        # pero las operaciones, que piden el permiso sin ``obj``, se habilitan.
        if obj is not None:
            return False
        # Saltea SoloLecturaAdminMixin: el permiso real del admin.
        return SisocModelAdmin.has_change_permission(self, request)


@admin.register(NotificacionPapel)
class NotificacionPapelAdmin(SoloLecturaAdmin):
    list_display = ("acta", "version", "condicion_firma", "cargada_at")
    list_filter = (
        ("condicion_firma", ChoicesDropdownFilter),
        ("cargada_at", RangeDateTimeFilter),
    )
    list_select_related = ("acta",)
    search_fields = ("acta__numero",)


@admin.register(EventoInspeccion)
class EventoInspeccionAdmin(SoloLecturaAdmin):
    list_display = ("at", "accion", "actor_nombre", "inspeccion", "acta")
    list_filter = (("accion", ChoicesDropdownFilter), ("at", RangeDateTimeFilter))
    list_select_related = ("inspeccion", "acta")
    search_fields = ("acta__numero", "actor_nombre")
