from django.contrib import admin
from django.core.exceptions import ValidationError
from unfold.contrib.filters.admin import (
    ChoicesDropdownFilter,
    RangeDateFilter,
    RangeDateTimeFilter,
)

from core.admin_base import SisocModelAdmin
from core.admin_operaciones import Operacion, OperacionesAdminMixin
from centrodefamilia.services.participante import ParticipanteService
from .models import (
    Actividad,
    AccesoCDF,
    Beneficiario,
    CabalArchivo,
    Categoria,
    Centro,
    InformeCabalRegistro,
    ParticipanteActividad,
    ParticipanteActividadHistorial,
    Responsable,
)


# Operación de soporte (issue #2789): misma llamada que
# ParticipanteActividadDeleteView. El service promueve al primero de la lista
# de espera.


def dar_de_baja_participante(participante, usuario, _datos):
    # El service no falla con un participante ya dado de baja: lo devuelve sin
    # cambios. En el admin eso se informa como error para no auditar una baja
    # que no ocurrió.
    if participante.estado == "dado_baja":
        raise ValidationError("El participante ya está dado de baja.")
    return ParticipanteService.dar_de_baja(participante.pk, usuario)


@admin.register(Centro)
class CentroAdmin(SisocModelAdmin):
    list_display = ("nombre", "tipo", "activo", "faro_asociado")
    list_select_related = ("faro_asociado",)
    list_filter = ("tipo", "activo")
    search_fields = ("nombre",)


@admin.register(Categoria)
class CategoriaAdmin(SisocModelAdmin):
    list_display = ("nombre",)
    search_fields = ("nombre",)


@admin.register(Actividad)
class ActividadAdmin(SisocModelAdmin):
    list_display = ("nombre", "categoria")
    list_select_related = ("categoria",)
    list_filter = ("categoria",)
    search_fields = ("nombre",)


class ActividadCentroAdmin(SisocModelAdmin):
    list_display = (
        "centro",
        "actividad",
        "get_categoria",
        "cantidad_personas",
        "dias",
        "horariosdesde",
        "horarioshasta",
    )
    list_filter = ("centro", "actividad", "actividad__categoria")

    def get_categoria(self, obj):
        return obj.actividad.categoria

    get_categoria.short_description = "Categoría"


# ``str(actividad_centro)`` muestra actividad y centro.
SELECT_ACTIVIDAD_CENTRO = ("actividad_centro__actividad", "actividad_centro__centro")


@admin.register(ParticipanteActividad)
class ParticipanteActividadAdmin(OperacionesAdminMixin, SisocModelAdmin):
    list_display = ("actividad_centro", "ciudadano", "estado", "fecha_registro")
    list_select_related = ("ciudadano", *SELECT_ACTIVIDAD_CENTRO)
    search_fields = (
        "=id",
        "ciudadano__documento",
        "ciudadano__apellido",
        "ciudadano__nombre",
    )
    list_filter = (
        ("estado", ChoicesDropdownFilter),
        ("fecha_registro", RangeDateTimeFilter),
        "actividad_centro__centro",
    )
    autocomplete_fields = ("ciudadano",)
    raw_id_fields = ("actividad_centro",)
    operaciones = (
        Operacion(
            slug="dar_de_baja",
            titulo="Dar de baja de la actividad",
            descripcion="Libera el lugar y promueve al primero de la lista de espera.",
            ejecutar=dar_de_baja_participante,
            campo_estado="estado",
            motivo_obligatorio=True,
            destructiva=True,
            icono="person_remove",
        ),
    )


@admin.register(ParticipanteActividadHistorial)
class ParticipanteActividadHistorialAdmin(SisocModelAdmin):
    """Historial de inscripciones: lo escribe ParticipanteService."""

    list_display = (
        "participante",
        "estado_anterior",
        "estado_nuevo",
        "usuario",
        "fecha_cambio",
    )
    list_select_related = (
        "participante__ciudadano",
        "participante__actividad_centro__actividad",
        "participante__actividad_centro__centro",
        "usuario",
    )
    list_filter = (
        ("estado_nuevo", ChoicesDropdownFilter),
        ("fecha_cambio", RangeDateTimeFilter),
    )
    search_fields = (
        "=participante__id",
        "participante__ciudadano__documento",
        "participante__ciudadano__apellido",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Responsable)
class ResponsableAdmin(SisocModelAdmin):
    list_display = ("apellido", "nombre", "dni", "cuil", "vinculo_parental", "genero")
    list_filter = ("vinculo_parental", "genero", "provincia")
    search_fields = ("apellido", "nombre", "dni", "cuil")
    raw_id_fields = ("creado_por",)
    readonly_fields = ("fecha_creado", "fecha_modificado")


@admin.register(Beneficiario)
class BeneficiarioAdmin(SisocModelAdmin):
    list_display = (
        "apellido",
        "nombre",
        "dni",
        "cuil",
        "genero",
        "maximo_nivel_educativo",
    )
    list_filter = ("genero", "maximo_nivel_educativo", "estado_academico")
    search_fields = ("apellido", "nombre", "dni", "cuil")
    raw_id_fields = ("responsable", "creado_por")
    readonly_fields = ("actividad_preferida", "fecha_creado", "fecha_modificado")


@admin.register(AccesoCDF)
class AccesoCDFAdmin(SisocModelAdmin):
    list_display = ("user", "centro", "activo", "fecha_creacion")
    list_select_related = ("user", "centro")
    list_filter = ("activo", ("fecha_creacion", RangeDateTimeFilter))
    search_fields = ("user__username", "user__email", "centro__nombre")
    raw_id_fields = ("user", "creado_por")
    readonly_fields = ("fecha_creacion", "fecha_baja")


@admin.register(CabalArchivo)
class CabalArchivoAdmin(SisocModelAdmin):
    list_display = (
        "nombre_original",
        "usuario",
        "fecha_subida",
        "total_filas",
        "total_validas",
        "total_invalidas",
    )
    list_select_related = ("usuario",)
    list_filter = (("fecha_subida", RangeDateTimeFilter),)
    search_fields = ("nombre_original",)
    raw_id_fields = ("usuario",)
    readonly_fields = (
        "fecha_subida",
        "total_filas",
        "total_validas",
        "total_invalidas",
    )


@admin.register(InformeCabalRegistro)
class InformeCabalRegistroAdmin(SisocModelAdmin):
    list_display = (
        "archivo",
        "centro",
        "nro_comercio",
        "razon_social",
        "importe",
        "fecha_trx",
        "no_coincidente",
    )
    list_select_related = ("archivo", "centro")
    list_filter = ("no_coincidente", ("fecha_trx", RangeDateFilter))
    search_fields = ("nro_comercio", "razon_social", "nro_tarjeta")
    raw_id_fields = ("archivo", "centro")
    date_hierarchy = "fecha_trx"
    list_per_page = 50
