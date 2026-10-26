from django.contrib import admin
from core.admin_base import SisocModelAdmin


from relevamientos.models import (
    ActividadesExtrasSeguimiento,
    AlmacenamientoAlimentosSeguimiento,
    AsistenciaTecnicaSeguimiento,
    CantidadColaboradores,
    CierreSeguimiento,
    ComprasSeguimiento,
    CondicionesHigieneSeguimiento,
    FrecuenciaLimpieza,
    FrecuenciaAlimentosSeguimiento,
    FrecuenciaCompraAlimentosSeguimiento,
    FrecuenciaRecepcionRecursos,
    FuenteCompras,
    FuenteRecursos,
    FuncionamientoSeguimiento,
    ItemRecetaSeguimiento,
    MenuSeguimiento,
    TipoAgua,
    TipoCombustible,
    TipoDesague,
    TipoEspacio,
    TipoGestionQuejas,
    TipoModalidadPrestacion,
    TipoRecurso,
    Excepcion,
    MotivoExcepcion,
    Prestacion,
    PrestacionSeguimiento,
    PrimerSeguimiento,
    Relevamiento,
    RegistroAsistenciaSeguimiento,
    RendicionCuentasSeguimiento,
    RecursosSeguimiento,
    SeguimientoPnud,
    ServiciosBasicosSeguimiento,
    TareasComedorSeguimiento,
    TarjetaSeguimiento,
)

admin.site.register(TipoModalidadPrestacion, SisocModelAdmin)
admin.site.register(TipoEspacio, SisocModelAdmin)
admin.site.register(TipoCombustible, SisocModelAdmin)
admin.site.register(TipoAgua, SisocModelAdmin)
admin.site.register(TipoDesague, SisocModelAdmin)
admin.site.register(FrecuenciaLimpieza, SisocModelAdmin)
admin.site.register(CantidadColaboradores, SisocModelAdmin)
admin.site.register(FrecuenciaRecepcionRecursos, SisocModelAdmin)
admin.site.register(TipoGestionQuejas, SisocModelAdmin)
admin.site.register(TipoRecurso, SisocModelAdmin)
admin.site.register(FuenteRecursos, SisocModelAdmin)
admin.site.register(FuenteCompras, SisocModelAdmin)
admin.site.register(Prestacion, SisocModelAdmin)
admin.site.register(Relevamiento, SisocModelAdmin)
admin.site.register(MotivoExcepcion, SisocModelAdmin)
admin.site.register(Excepcion, SisocModelAdmin)
admin.site.register(FuncionamientoSeguimiento, SisocModelAdmin)
admin.site.register(ServiciosBasicosSeguimiento, SisocModelAdmin)
admin.site.register(AlmacenamientoAlimentosSeguimiento, SisocModelAdmin)
admin.site.register(CondicionesHigieneSeguimiento, SisocModelAdmin)
admin.site.register(TareasComedorSeguimiento, SisocModelAdmin)
admin.site.register(RecursosSeguimiento, SisocModelAdmin)
admin.site.register(ComprasSeguimiento, SisocModelAdmin)
admin.site.register(FrecuenciaCompraAlimentosSeguimiento, SisocModelAdmin)
admin.site.register(MenuSeguimiento, SisocModelAdmin)
admin.site.register(RegistroAsistenciaSeguimiento, SisocModelAdmin)
admin.site.register(FrecuenciaAlimentosSeguimiento, SisocModelAdmin)
admin.site.register(ActividadesExtrasSeguimiento, SisocModelAdmin)
admin.site.register(TarjetaSeguimiento, SisocModelAdmin)
admin.site.register(RendicionCuentasSeguimiento, SisocModelAdmin)
admin.site.register(AsistenciaTecnicaSeguimiento, SisocModelAdmin)
admin.site.register(CierreSeguimiento, SisocModelAdmin)
admin.site.register(PrimerSeguimiento, SisocModelAdmin)
admin.site.register(PrestacionSeguimiento, SisocModelAdmin)
admin.site.register(ItemRecetaSeguimiento, SisocModelAdmin)


@admin.register(SeguimientoPnud)
class SeguimientoPnudAdmin(SisocModelAdmin):
    list_display = (
        "id",
        "comedor",
        "formulario",
        "fecha_hora",
        "tecnico",
        "estado_validacion",
        "origen",
    )
    list_filter = ("formulario", "estado_validacion", "origen")
    list_select_related = ("comedor", "tecnico")
    search_fields = ("comedor__nombre", "client_uuid")
    raw_id_fields = ("comedor", "tecnico", "coordinador")
    readonly_fields = ("client_uuid", "fecha_creacion", "fecha_actualizacion")
