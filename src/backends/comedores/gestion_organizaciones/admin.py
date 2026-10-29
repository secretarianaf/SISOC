from django.contrib import admin

from core.admin_base import SisocModelAdmin
from gestion_organizaciones.models import Firmante


@admin.register(Firmante)
class FirmanteAdmin(SisocModelAdmin):
    list_display = ("nombre", "cuit", "rol", "organizacion", "programa")
    list_select_related = ("rol", "organizacion", "programa")
    list_filter = ("rol", "programa")
    search_fields = ("nombre", "cuit", "organizacion__nombre", "organizacion__cuit")
    raw_id_fields = ("organizacion",)
