from django.contrib import admin
from unfold.contrib.filters.admin import RangeDateTimeFilter

from core.admin_base import SisocModelAdmin
from duplas.models import Dupla


@admin.register(Dupla)
class DuplaAdmin(SisocModelAdmin):
    list_display = ("id", "nombre", "estado", "abogado", "coordinador", "fecha")
    list_select_related = ("abogado", "coordinador")
    list_filter = ("estado", ("fecha", RangeDateTimeFilter))
    search_fields = ("nombre", "abogado__username", "coordinador__username")
    raw_id_fields = ("tecnico", "abogado", "coordinador", "coordinadores")
