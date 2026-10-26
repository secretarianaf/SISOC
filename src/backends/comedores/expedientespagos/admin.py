from django.contrib import admin
from unfold.contrib.filters.admin import (
    AutocompleteSelectFilter,
    RangeDateFilter,
    RangeDateTimeFilter,
)

from core.admin_base import SisocModelAdmin
from expedientespagos.models import ExpedientePago


@admin.register(ExpedientePago)
class ExpedientePagoAdmin(SisocModelAdmin):
    list_display = (
        "id",
        "expediente_pago",
        "expediente_convenio",
        "comedor",
        "mes_pago",
        "ano",
        "total",
        "fecha_pago_al_banco",
        "fecha_acreditacion",
    )
    list_select_related = ("comedor",)
    list_filter = (
        "ano",
        ("fecha_pago_al_banco", RangeDateFilter),
        ("fecha_acreditacion", RangeDateFilter),
        ("fecha_creacion", RangeDateTimeFilter),
        ("comedor", AutocompleteSelectFilter),
    )
    search_fields = (
        "expediente_pago",
        "expediente_convenio",
        "numero_orden_pago",
        "comedor__nombre",
    )
    autocomplete_fields = ("comedor",)
