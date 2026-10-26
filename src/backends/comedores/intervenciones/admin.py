from django.contrib import admin
from unfold.contrib.filters.admin import AutocompleteSelectFilter, RangeDateTimeFilter

from core.admin_base import SisocModelAdmin
from intervenciones.models.intervenciones import Intervencion


# Intervencion registra actividad de negocio con soft delete y signals que crean
# hitos: no se habilita import/export desde admin. Los catálogos se administran
# desde catalogo_intervenciones (kernel).
@admin.register(Intervencion)
class IntervencionAdmin(SisocModelAdmin):
    list_display = (
        "id",
        "comedor",
        "tipo_intervencion",
        "subintervencion",
        "fecha",
        "tiene_documentacion",
    )
    list_select_related = ("comedor", "tipo_intervencion", "subintervencion")
    list_filter = (
        "tipo_intervencion",
        "tiene_documentacion",
        ("fecha", RangeDateTimeFilter),
        ("comedor", AutocompleteSelectFilter),
    )
    search_fields = ("comedor__nombre", "observaciones")
    autocomplete_fields = ("comedor",)
    raw_id_fields = ("admision",)
