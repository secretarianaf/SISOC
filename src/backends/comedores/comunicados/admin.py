from django.contrib import admin
from core.admin_base import SisocModelAdmin, SisocTabularInline
from .models import Comunicado, ComunicadoAdjunto


class ComunicadoAdjuntoInline(SisocTabularInline):
    model = ComunicadoAdjunto
    extra = 1


@admin.register(Comunicado)
class ComunicadoAdmin(SisocModelAdmin):
    list_display = [
        "titulo",
        "estado",
        "destacado",
        "fecha_publicacion",
        "usuario_creador",
    ]
    list_filter = ["estado", "destacado", "fecha_publicacion"]
    search_fields = ["titulo", "cuerpo"]
    readonly_fields = ["fecha_creacion", "fecha_publicacion"]
    inlines = [ComunicadoAdjuntoInline]


@admin.register(ComunicadoAdjunto)
class ComunicadoAdjuntoAdmin(SisocModelAdmin):
    list_display = ["nombre_original", "comunicado", "fecha_subida"]
    list_filter = ["fecha_subida"]
    search_fields = ["nombre_original", "comunicado__titulo"]
