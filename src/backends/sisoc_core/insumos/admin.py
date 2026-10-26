from django.contrib import admin
from unfold.contrib.filters.admin import RangeDateTimeFilter, RelatedDropdownFilter

from core.admin_base import SisocModelAdmin
from .models import Insumo, InsumoCategoria


@admin.register(InsumoCategoria)
class InsumoCategoriaAdmin(SisocModelAdmin):
    list_display = ("nombre", "programa", "orden", "activo", "fecha_creacion")
    list_filter = (("programa", RelatedDropdownFilter), "activo")
    search_fields = ("nombre",)
    list_select_related = ("programa",)


@admin.register(Insumo)
class InsumoAdmin(SisocModelAdmin):
    list_display = (
        "titulo",
        "categoria",
        "programa",
        "activo",
        "usuario_creacion",
        "fecha_creacion",
    )
    list_filter = (
        ("programa", RelatedDropdownFilter),
        ("categoria", RelatedDropdownFilter),
        "activo",
        ("fecha_creacion", RangeDateTimeFilter),
    )
    search_fields = ("titulo", "descripcion")
    list_select_related = ("categoria", "programa", "usuario_creacion")
    readonly_fields = ("usuario_creacion", "usuario_actualizacion")
