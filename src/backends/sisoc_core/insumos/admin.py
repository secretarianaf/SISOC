from django.contrib import admin

from core.admin_base import SisocModelAdmin
from .models import Insumo, InsumoCategoria


@admin.register(InsumoCategoria)
class InsumoCategoriaAdmin(SisocModelAdmin):
    list_display = ("nombre", "programa", "orden", "activo", "fecha_creacion")
    list_filter = ("programa", "activo")
    search_fields = ("nombre",)


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
    list_filter = ("programa", "categoria", "activo")
    search_fields = ("titulo", "descripcion")
    readonly_fields = ("usuario_creacion", "usuario_actualizacion")
