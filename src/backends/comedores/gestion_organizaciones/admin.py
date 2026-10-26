from django.contrib import admin

from core.admin_base import SisocModelAdmin
from gestion_organizaciones.models import (
    ConvenioProyecto,
    DatosRegionOrganizacion,
    Firmante,
    LineaProyecto,
    ProgramaOrganizacion,
    RegionAbordaje,
    SubzonaAbordaje,
)

admin.site.register(Firmante, SisocModelAdmin)


@admin.register(ProgramaOrganizacion)
class ProgramaOrganizacionAdmin(SisocModelAdmin):
    list_display = ("organizacion", "programa", "fecha_creacion")
    list_filter = ("programa",)
    search_fields = ("organizacion__nombre", "organizacion__cuit")
    raw_id_fields = ("organizacion",)


@admin.register(LineaProyecto)
class LineaProyectoAdmin(SisocModelAdmin):
    list_display = ("proyecto", "programa")
    list_filter = ("programa",)
    search_fields = ("proyecto__codigo", "proyecto__organizacion__nombre")
    raw_id_fields = ("proyecto",)


@admin.register(RegionAbordaje)
class RegionAbordajeAdmin(SisocModelAdmin):
    list_display = ("nombre",)
    search_fields = ("nombre",)


@admin.register(SubzonaAbordaje)
class SubzonaAbordajeAdmin(SisocModelAdmin):
    list_display = ("nombre", "region")
    list_filter = ("region",)
    search_fields = ("nombre",)


@admin.register(DatosRegionOrganizacion)
class DatosRegionOrganizacionAdmin(SisocModelAdmin):
    list_display = ("organizacion", "region", "subzona")
    list_filter = ("region",)
    search_fields = ("organizacion__nombre",)
    raw_id_fields = ("organizacion",)


@admin.register(ConvenioProyecto)
class ConvenioProyectoAdmin(SisocModelAdmin):
    list_display = ("proyecto", "numero", "fecha", "meses", "monto_total")
    search_fields = ("numero", "proyecto__codigo", "proyecto__organizacion__nombre")
    raw_id_fields = ("proyecto",)
