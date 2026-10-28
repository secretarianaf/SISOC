from django.contrib import admin
from unfold.contrib.filters.admin import RangeDateTimeFilter

from core.admin_base import SisocModelAdmin
from dispositivos.models import Dispositivo


@admin.register(Dispositivo)
class DispositivoAdmin(SisocModelAdmin):
    list_display = (
        "nombre_institucion",
        "tipo_dispositivo",
        "provincia",
        "municipio",
        "created_at",
    )
    list_select_related = ("provincia", "municipio")
    search_fields = (
        "=id",
        "nombre_institucion",
        "razon_social",
        "cuit_institucion",
    )
    list_filter = (
        "tipo_dispositivo",
        "modalidad_funcionamiento",
        "provincia",
        ("created_at", RangeDateTimeFilter),
    )
