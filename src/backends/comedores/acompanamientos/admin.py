from django.contrib import admin
from unfold.contrib.filters.admin import RangeDateTimeFilter

from core.admin_base import SisocModelAdmin
from acompanamientos.models.acompanamiento import (
    Acompanamiento,
    InformacionRelevante,
    Prestacion,
)
from acompanamientos.models.hitos import Hitos, HitosIntervenciones


# acompañamientos
@admin.register(Acompanamiento)
class AcompanamientoAdmin(SisocModelAdmin):
    list_display = ("id", "admision", "nro_convenio", "fecha_creacion")
    list_select_related = ("admision",)
    list_filter = (("fecha_creacion", RangeDateTimeFilter),)
    search_fields = ("nro_convenio", "admision__comedor__nombre")
    raw_id_fields = ("admision",)


@admin.register(InformacionRelevante)
class InformacionRelevanteAdmin(SisocModelAdmin):
    list_display = (
        "id",
        "acompanamiento",
        "numero_expediente",
        "numero_resolucion",
        "vencimiento_mandato",
    )
    list_select_related = ("acompanamiento",)
    search_fields = (
        "numero_expediente",
        "numero_resolucion",
        "if_relevamiento",
        "acompanamiento__nro_convenio",
    )
    raw_id_fields = ("acompanamiento",)


@admin.register(Prestacion)
class PrestacionAdmin(SisocModelAdmin):
    list_display = ("id", "acompanamiento", "dia", "desayuno", "almuerzo", "merienda")
    list_select_related = ("acompanamiento",)
    list_filter = ("dia",)
    search_fields = ("acompanamiento__nro_convenio",)
    raw_id_fields = ("acompanamiento",)


# hitos
@admin.register(Hitos)
class HitosAdmin(SisocModelAdmin):
    list_display = ("id", "acompanamiento", "fecha")
    list_select_related = ("acompanamiento",)
    list_filter = (("fecha", RangeDateTimeFilter),)
    search_fields = ("acompanamiento__nro_convenio",)
    raw_id_fields = ("acompanamiento",)


@admin.register(HitosIntervenciones)
class HitosIntervencionesAdmin(SisocModelAdmin):
    list_display = ("id", "intervencion", "subintervencion", "hito")
    search_fields = ("intervencion", "subintervencion", "hito")
