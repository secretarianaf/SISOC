from django.contrib import admin
from unfold.contrib.filters.admin import RangeDateTimeFilter, RelatedDropdownFilter

from core.admin_base import SisocModelAdmin
from rendicioncuentasfinal.models import (
    DocumentoRendicionFinal,
    EstadoDocumentoRendicionFinal,
    RendicionCuentasFinal,
    TipoDocumentoRendicionFinal,
)


@admin.register(RendicionCuentasFinal)
class RendicionCuentasFinalAdmin(SisocModelAdmin):
    list_display = ("id", "comedor", "fisicamente_presentada")
    list_select_related = ("comedor",)
    search_fields = ("=id", "comedor__nombre", "comedor__codigo_de_proyecto")
    list_filter = ("fisicamente_presentada",)
    raw_id_fields = ("comedor",)


@admin.register(EstadoDocumentoRendicionFinal)
class EstadoDocumentoRendicionFinalAdmin(SisocModelAdmin):
    list_display = ("id", "nombre")
    search_fields = ("nombre",)


@admin.register(TipoDocumentoRendicionFinal)
class TipoDocumentoRendicionFinalAdmin(SisocModelAdmin):
    list_display = ("id", "nombre", "validador", "personalizado")
    list_filter = ("validador", "personalizado")
    search_fields = ("nombre",)


@admin.register(DocumentoRendicionFinal)
class DocumentoRendicionFinalAdmin(SisocModelAdmin):
    list_display = (
        "id",
        "rendicion_final",
        "tipo",
        "estado",
        "fecha_modificacion",
    )
    list_select_related = ("rendicion_final", "tipo", "estado")
    search_fields = (
        "=id",
        "=rendicion_final__id",
        "rendicion_final__comedor__nombre",
        "tipo__nombre",
    )
    list_filter = (
        ("estado", RelatedDropdownFilter),
        "tipo__validador",
        ("fecha_modificacion", RangeDateTimeFilter),
    )
    raw_id_fields = ("rendicion_final",)
