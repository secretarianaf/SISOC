from django.contrib import admin
from unfold.contrib.filters.admin import (
    ChoicesDropdownFilter,
    RangeDateFilter,
    RangeDateTimeFilter,
    RelatedDropdownFilter,
)

from core.admin_base import SisocModelAdmin
from core.admin_import_export import BaseImportExportAdmin
from organizaciones.models import (
    ArchivoOrganizacion,
    DocumentacionOrganizacion,
    Organizacion,
    ProyectoOrganizacion,
    RolFirmante,
    TipoOrganizacion,
)

# Organizacion y sus documentos manejan soft delete, archivos y firmantes con
# reglas propias: quedan sin import/export por ahora.


@admin.register(Organizacion)
class OrganizacionAdmin(SisocModelAdmin):
    list_display = ("id", "nombre", "sigla", "cuit", "provincia", "fecha_creacion")
    # Organizacion es destino de autocomplete de otros dominios: se busca por
    # nombre, sigla o CUIT.
    search_fields = ("nombre", "sigla", "cuit")
    list_filter = (
        ("provincia", RelatedDropdownFilter),
        ("tipo_entidad", RelatedDropdownFilter),
        "sin_vencimiento",
        ("fecha_vencimiento", RangeDateTimeFilter),
        ("fecha_creacion", RangeDateTimeFilter),
    )
    list_select_related = ("provincia",)
    autocomplete_fields = (
        "provincia",
        "municipio",
        "localidad",
        "territoriales_abordaje_comunitario",
        "deleted_by",
    )
    readonly_fields = ("fecha_creacion",)


@admin.register(ProyectoOrganizacion)
class ProyectoOrganizacionAdmin(SisocModelAdmin):
    list_display = ("codigo", "nombre", "organizacion", "activo")
    search_fields = ("codigo", "nombre", "organizacion__nombre", "organizacion__cuit")
    list_filter = ("activo",)
    list_select_related = ("organizacion",)
    autocomplete_fields = ("organizacion",)


@admin.register(DocumentacionOrganizacion)
class DocumentacionOrganizacionAdmin(SisocModelAdmin):
    list_display = ("nombre", "categoria", "obligatorio", "orden")
    search_fields = ("nombre",)
    list_filter = ("categoria", "obligatorio")


@admin.register(ArchivoOrganizacion)
class ArchivoOrganizacionAdmin(SisocModelAdmin):
    list_display = (
        "organizacion",
        "documentacion",
        "nombre_personalizado",
        "estado",
        "fecha_vencimiento",
        "creado",
    )
    search_fields = (
        "organizacion__nombre",
        "organizacion__cuit",
        "nombre_personalizado",
        "numero_gde",
    )
    list_filter = (
        ("estado", ChoicesDropdownFilter),
        ("documentacion", RelatedDropdownFilter),
        ("fecha_vencimiento", RangeDateFilter),
        ("creado", RangeDateTimeFilter),
    )
    list_select_related = ("organizacion", "documentacion")
    autocomplete_fields = ("organizacion", "creado_por", "modificado_por", "deleted_by")
    readonly_fields = ("creado", "modificado")



@admin.register(TipoOrganizacion)
class TipoOrganizacionAdmin(BaseImportExportAdmin):
    list_display = ("id", "nombre")
    search_fields = ("nombre",)


@admin.register(RolFirmante)
class RolFirmanteAdmin(BaseImportExportAdmin):
    list_display = ("id", "nombre")
    search_fields = ("nombre",)
