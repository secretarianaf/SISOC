"""Admin de DataCalle (issue #2789).

Los operativos se planifican desde el backoffice (``/datacalle/``) y los casos
llegan desde la app. Desde acá soporte busca, filtra y corrige el estado del
operativo con los mismos services que usan la pantalla y la API.
"""

from django.contrib import admin
from django.core.exceptions import ValidationError
from unfold.contrib.filters.admin import (
    ChoicesDropdownFilter,
    RangeDateFilter,
    RangeDateTimeFilter,
)

from core.admin_base import SisocModelAdmin
from core.admin_operaciones import Operacion, OperacionesAdminMixin
from datacalle.models import Encuesta, Relevamiento
from datacalle.services import cerrar_relevamiento


def cerrar(relevamiento, usuario, _datos):
    _, cerrado_ahora = cerrar_relevamiento(relevamiento=relevamiento, user=usuario)
    if not cerrado_ahora:
        raise ValidationError("El relevamiento ya estaba cerrado.")


@admin.register(Relevamiento)
class RelevamientoAdmin(OperacionesAdminMixin, SisocModelAdmin):
    list_display = (
        "denominacion",
        "provincia",
        "municipio",
        "fase",
        "estado",
        "fecha_inicio",
        "fecha_fin",
        "modalidad_papel",
    )
    list_filter = (
        ("estado", ChoicesDropdownFilter),
        "fase",
        "modalidad_papel",
        "provincia",
        ("fecha_inicio", RangeDateFilter),
        ("fecha_cierre", RangeDateTimeFilter),
    )
    list_select_related = ("provincia", "municipio")
    search_fields = (
        "denominacion",
        "area_operativa",
        "dispositivo__nombre_institucion",
    )
    # Localidades y usuarios son tablas grandes: un select con todas las
    # opciones haría pesado el form.
    raw_id_fields = (
        "municipio",
        "dispositivo",
        "localidades",
        "equipo",
        "cerrado_por",
        "creado_por",
    )
    readonly_fields = ("fecha_cierre", "created_at", "updated_at")
    operaciones = (
        Operacion(
            slug="cerrar",
            titulo="Cerrar relevamiento",
            descripcion=(
                "Finaliza el operativo: la app deja de aceptar casos. No hay "
                "operación para reabrirlo."
            ),
            ejecutar=cerrar,
            campo_estado="estado",
            motivo_obligatorio=True,
            destructiva=True,
            icono="lock",
        ),
    )


@admin.register(Encuesta)
class EncuestaAdmin(SisocModelAdmin):
    """Casos de la app: evidencia de campo, de sólo lectura."""

    list_display = (
        "id",
        "relevamiento",
        "estado",
        "origen",
        "variante",
        "fecha_inicio",
        "relevador",
    )
    list_filter = (
        ("estado", ChoicesDropdownFilter),
        "origen",
        ("fecha_inicio", RangeDateTimeFilter),
        ("created_at", RangeDateTimeFilter),
    )
    list_select_related = ("relevamiento", "relevador")
    # Sin ``codigo_entrevistado``: es el identificador de la persona que
    # audittrail ya excluye de los cambios (ver Encuesta.__str__).
    search_fields = ("relevamiento__denominacion", "relevador__username")

    def get_queryset(self, request):
        # El listado no necesita el JSON del instrumento: ordenarlo con filas
        # anchas agota el sort buffer de MySQL (ver services/encuestas.py).
        return super().get_queryset(request).defer("respuestas")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
