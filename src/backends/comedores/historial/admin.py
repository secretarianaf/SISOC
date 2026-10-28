from django.contrib import admin
from unfold.contrib.filters.admin import RangeDateTimeFilter

from core.admin_base import SisocModelAdmin
from historial.models import Historial


@admin.register(Historial)
class HistorialAdmin(SisocModelAdmin):
    """Historial de acciones: solo consulta."""

    list_display = ("fecha", "usuario", "accion", "content_type", "object_id")
    list_select_related = ("usuario", "content_type")
    list_filter = ("content_type", ("fecha", RangeDateTimeFilter))
    search_fields = ("accion", "object_id", "usuario__username")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
