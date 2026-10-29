from django.contrib import admin
from unfold.contrib.filters.admin import RangeDateFilter

from core.admin_base import SisocModelAdmin
from gestion_organizaciones.models import (
    ConvenioProyecto,
    Firmante,
    LineaProyecto,
    ProgramaOrganizacion,
)


@admin.register(Firmante)
class FirmanteAdmin(SisocModelAdmin):
    list_display = ("nombre", "cuit", "rol", "organizacion", "programa")
    list_select_related = ("rol", "organizacion", "programa")
    list_filter = ("rol", "programa")
    search_fields = ("nombre", "cuit", "organizacion__nombre", "organizacion__cuit")
    raw_id_fields = ("organizacion",)


@admin.register(ProgramaOrganizacion)
class ProgramaOrganizacionAdmin(SisocModelAdmin):
    list_display = ("organizacion", "programa", "fecha_creacion")
    list_select_related = ("organizacion", "programa")
    list_filter = ("programa",)
    search_fields = ("organizacion__nombre", "organizacion__cuit")
    raw_id_fields = ("organizacion",)


@admin.register(LineaProyecto)
class LineaProyectoAdmin(SisocModelAdmin):
    list_display = ("proyecto", "programa")
    list_select_related = ("proyecto", "programa")
    list_filter = ("programa",)
    search_fields = ("proyecto__codigo", "proyecto__organizacion__nombre")
    raw_id_fields = ("proyecto",)


@admin.register(ConvenioProyecto)
class ConvenioProyectoAdmin(SisocModelAdmin):
    list_display = ("proyecto", "numero", "fecha", "meses", "monto_total")
    list_select_related = ("proyecto",)
    list_filter = (("fecha", RangeDateFilter),)
    search_fields = ("numero", "proyecto__codigo", "proyecto__organizacion__nombre")
    raw_id_fields = ("proyecto",)
