from django.contrib import admin

from gestion_organizaciones.models import (
    ConvenioProyecto,
    DatosRegionOrganizacion,
    Firmante,
    LineaProyecto,
    ProgramaOrganizacion,
    RegionAbordaje,
    SubzonaAbordaje,
)

admin.site.register(Firmante)


@admin.register(ProgramaOrganizacion)
class ProgramaOrganizacionAdmin(admin.ModelAdmin):
    list_display = ("organizacion", "programa", "fecha_creacion")
    list_filter = ("programa",)
    search_fields = ("organizacion__nombre", "organizacion__cuit")
    raw_id_fields = ("organizacion",)


@admin.register(LineaProyecto)
class LineaProyectoAdmin(admin.ModelAdmin):
    list_display = ("proyecto", "programa")
    list_filter = ("programa",)
    search_fields = ("proyecto__codigo", "proyecto__organizacion__nombre")
    raw_id_fields = ("proyecto",)


@admin.register(RegionAbordaje)
class RegionAbordajeAdmin(admin.ModelAdmin):
    list_display = ("nombre",)
    search_fields = ("nombre",)


@admin.register(SubzonaAbordaje)
class SubzonaAbordajeAdmin(admin.ModelAdmin):
    list_display = ("nombre", "region")
    list_filter = ("region",)
    search_fields = ("nombre",)


@admin.register(DatosRegionOrganizacion)
class DatosRegionOrganizacionAdmin(admin.ModelAdmin):
    list_display = ("organizacion", "region", "subzona")
    list_filter = ("region",)
    search_fields = ("organizacion__nombre",)
    raw_id_fields = ("organizacion",)


@admin.register(ConvenioProyecto)
class ConvenioProyectoAdmin(admin.ModelAdmin):
    list_display = ("proyecto", "numero", "fecha", "meses", "monto_total")
    search_fields = ("numero", "proyecto__codigo", "proyecto__organizacion__nombre")
    raw_id_fields = ("proyecto",)
