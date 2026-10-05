from django.contrib import admin

from catalogo_intervenciones.models import (
    SubIntervencion,
    TipoContacto,
    TipoDestinatario,
    TipoIntervencion,
)
from catalogo_intervenciones.resources import (
    SubIntervencionResource,
    TipoIntervencionResource,
)
from core.admin_import_export import BaseImportExportAdmin


@admin.register(TipoIntervencion)
class TipoIntervencionAdmin(BaseImportExportAdmin):
    resource_classes = [TipoIntervencionResource]
    list_display = ("id", "nombre", "programa")
    list_filter = ("programa",)
    search_fields = ("nombre",)


@admin.register(SubIntervencion)
class SubIntervencionAdmin(BaseImportExportAdmin):
    resource_classes = [SubIntervencionResource]
    list_display = ("id", "nombre", "tipo_intervencion")
    list_filter = ("tipo_intervencion",)
    search_fields = ("nombre",)


@admin.register(TipoDestinatario)
class TipoDestinatarioAdmin(BaseImportExportAdmin):
    list_display = ("id", "nombre")
    search_fields = ("nombre",)


@admin.register(TipoContacto)
class TipoContactoAdmin(BaseImportExportAdmin):
    list_display = ("id", "nombre")
    search_fields = ("nombre",)
