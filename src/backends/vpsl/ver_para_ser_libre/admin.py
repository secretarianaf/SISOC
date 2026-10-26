from django.contrib import admin

from core.admin_base import SisocModelAdmin
from ver_para_ser_libre.models import (
    CasoLaboratorioVPSL,
    ChecklistJornadaVPSL,
    CierreDiarioVPSL,
    HistorialChecklistSedeVPSL,
    HistorialCierreDiarioVPSL,
    HistorialEstadoVPSL,
    HistorialLaboratorioVPSL,
    ItinerarioVPSL,
    EvaluacionSedeItinerarioVPSL,
    JornadaVPSL,
    RegistroNominalVPSL,
    SedeVPSL,
    VehiculoVPSL,
)


@admin.register(ItinerarioVPSL)
class ItinerarioVPSLAdmin(SisocModelAdmin):
    list_display = ("codigo", "provincia", "fecha_inicio", "fecha_fin", "estado")
    list_filter = ("estado", "provincia")
    search_fields = ("codigo", "referente_nombre", "localidades_tentativas")


@admin.register(JornadaVPSL)
class JornadaVPSLAdmin(SisocModelAdmin):
    list_display = ("itinerario", "fecha", "sede", "localidad", "estado")
    list_filter = ("estado", "fecha")
    search_fields = ("sede", "referente_nombre", "itinerario__codigo")


@admin.register(VehiculoVPSL)
class VehiculoVPSLAdmin(SisocModelAdmin):
    list_display = ("id", "nombre", "orden", "activo")
    list_editable = ("orden", "activo")
    list_filter = ("activo",)
    search_fields = ("nombre",)
    actions = None

    def has_delete_permission(self, request, obj=None):
        if obj is not None and obj.jornadas.exists():
            return False
        return super().has_delete_permission(request, obj)


admin.site.register(ChecklistJornadaVPSL, SisocModelAdmin)
admin.site.register(RegistroNominalVPSL, SisocModelAdmin)
admin.site.register(CasoLaboratorioVPSL, SisocModelAdmin)
admin.site.register(CierreDiarioVPSL, SisocModelAdmin)
admin.site.register(HistorialEstadoVPSL, SisocModelAdmin)
admin.site.register(EvaluacionSedeItinerarioVPSL, SisocModelAdmin)
admin.site.register(SedeVPSL, SisocModelAdmin)
admin.site.register(HistorialChecklistSedeVPSL, SisocModelAdmin)
admin.site.register(HistorialLaboratorioVPSL, SisocModelAdmin)
admin.site.register(HistorialCierreDiarioVPSL, SisocModelAdmin)
