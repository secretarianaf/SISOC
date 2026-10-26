from django.contrib import admin

from core.admin_base import SisocModelAdmin
from .models import (
    Actividad,
    AccesoCDF,
    Beneficiario,
    CabalArchivo,
    Categoria,
    Centro,
    InformeCabalRegistro,
    ParticipanteActividad,
    Responsable,
)


@admin.register(Centro)
class CentroAdmin(SisocModelAdmin):
    list_display = ("nombre", "tipo", "activo", "faro_asociado")
    list_filter = ("tipo", "activo")
    search_fields = ("nombre",)


@admin.register(Categoria)
class CategoriaAdmin(SisocModelAdmin):
    list_display = ("nombre",)
    search_fields = ("nombre",)


@admin.register(Actividad)
class ActividadAdmin(SisocModelAdmin):
    list_display = ("nombre", "categoria")
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


@admin.register(ParticipanteActividad)
class ParticipanteActividadAdmin(SisocModelAdmin):
    list_display = ("actividad_centro", "ciudadano", "fecha_registro")
    search_fields = ("ciudadano__apellido", "ciudadano__nombre", "ciudadano__documento")
    list_filter = ("actividad_centro__centro",)


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
    list_filter = ("activo",)
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
    list_filter = ("no_coincidente",)
    search_fields = ("nro_comercio", "razon_social", "nro_tarjeta")
    raw_id_fields = ("archivo", "centro")
    date_hierarchy = "fecha_trx"
    list_per_page = 50
