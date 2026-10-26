from django.contrib import admin

from core.admin_base import SisocModelAdmin
from core.admin_import_export import BaseImportExportAdmin
from organizaciones.models import (
    ArchivoOrganizacion,
    DocumentacionOrganizacion,
    Organizacion,
    ProyectoOrganizacion,
    RolFirmante,
    TipoOrganizacion,
    RegionAbordajeComunitario,
    SubzonaAbordajeComunitario,
)

# Organizacion y sus documentos manejan soft delete, archivos y firmantes con
# reglas propias: quedan sin import/export por ahora.
admin.site.register(Organizacion, SisocModelAdmin)
admin.site.register(ProyectoOrganizacion, SisocModelAdmin)
admin.site.register(DocumentacionOrganizacion, SisocModelAdmin)
admin.site.register(ArchivoOrganizacion, SisocModelAdmin)
admin.site.register(RegionAbordajeComunitario, SisocModelAdmin)
admin.site.register(SubzonaAbordajeComunitario, SisocModelAdmin)


@admin.register(TipoOrganizacion)
class TipoOrganizacionAdmin(BaseImportExportAdmin):
    list_display = ("id", "nombre")
    search_fields = ("nombre",)


@admin.register(RolFirmante)
class RolFirmanteAdmin(BaseImportExportAdmin):
    list_display = ("id", "nombre")
    search_fields = ("nombre",)
