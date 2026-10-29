from django.conf import settings
from django.contrib import admin
from django.core.exceptions import ValidationError
from django.db import transaction
from unfold.contrib.filters.admin import ChoicesDropdownFilter, RangeDateTimeFilter

from core.admin_base import SisocModelAdmin
from core.admin_operaciones import Operacion, OperacionesAdminMixin


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
from relevamientos.tasks import (
    AsyncSendPrimerSeguimientoToGestionar,
    AsyncSendRelevamientoToGestionar,
)


# Operaciones de soporte (issue #2789): reintentan el alta en GESTIONAR de un
# registro que quedó sin sincronizar. Usan las mismas tareas que el alta
# original; el envío sale recién cuando confirma la transacción de la
# operación y es asincrónico: ``sincronizado_gestionar`` pasa a True solo
# cuando GESTIONAR confirma la fila (ver los logs si no cambia).


def _validar_reintento_gestionar(obj):
    if not getattr(settings, "GESTIONAR_INTEGRATION_ENABLED", False):
        raise ValidationError("La integración con GESTIONAR está deshabilitada.")
    if obj.sincronizado_gestionar:
        raise ValidationError("Ya está sincronizado con GESTIONAR.")


def reintentar_sync_relevamiento(relevamiento, _usuario, _datos):
    _validar_reintento_gestionar(relevamiento)
    relevamiento_id = relevamiento.pk
    transaction.on_commit(
        lambda: AsyncSendRelevamientoToGestionar(relevamiento_id).start()
    )


def reintentar_sync_primer_seguimiento(seguimiento, _usuario, _datos):
    _validar_reintento_gestionar(seguimiento)
    # El alta del seguimiento referencia al relevamiento: el flujo original
    # (primer_seguimiento_service) lo envía antes. Acá no se manda en cadena:
    # se pide reintentar primero el relevamiento.
    relevamiento = seguimiento.id_relevamiento
    if relevamiento is not None and not relevamiento.sincronizado_gestionar:
        raise ValidationError(
            "El relevamiento no está sincronizado con GESTIONAR: reintentá "
            f"primero el relevamiento {relevamiento.pk}."
        )
    seguimiento_id = seguimiento.pk
    transaction.on_commit(
        lambda: AsyncSendPrimerSeguimientoToGestionar(seguimiento_id).start()
    )


class CatalogoNombreAdmin(SisocModelAdmin):
    """Catálogos de opciones del relevamiento: se buscan por nombre."""

    list_display = ("id", "nombre")
    search_fields = ("nombre",)


for catalogo in (
    TipoModalidadPrestacion,
    TipoEspacio,
    TipoCombustible,
    TipoAgua,
    TipoDesague,
    FrecuenciaLimpieza,
    CantidadColaboradores,
    FrecuenciaRecepcionRecursos,
    TipoGestionQuejas,
    TipoRecurso,
    MotivoExcepcion,
):
    admin.site.register(catalogo, CatalogoNombreAdmin)

admin.site.register(FuenteRecursos, SisocModelAdmin)
admin.site.register(FuenteCompras, SisocModelAdmin)
admin.site.register(Prestacion, SisocModelAdmin)
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
admin.site.register(PrestacionSeguimiento, SisocModelAdmin)
admin.site.register(ItemRecetaSeguimiento, SisocModelAdmin)


@admin.register(Relevamiento)
class RelevamientoAdmin(OperacionesAdminMixin, SisocModelAdmin):
    list_display = (
        "id",
        "comedor",
        "estado",
        "estado_validacion",
        "fecha_visita",
        "territorial_user",
        "sincronizado_gestionar",
        "origen",
    )
    list_select_related = ("comedor", "territorial_user")
    search_fields = (
        "=id",
        "comedor__nombre",
        "comedor__codigo_de_proyecto",
        "numero_if",
        "territorial_user__username",
    )
    list_filter = (
        "estado",
        ("estado_validacion", ChoicesDropdownFilter),
        "sincronizado_gestionar",
        "origen",
        ("fecha_visita", RangeDateTimeFilter),
        ("fecha_creacion", RangeDateTimeFilter),
    )
    raw_id_fields = (
        "territorial_user",
        "responsable_relevamiento",
        "coordinador",
        "funcionamiento",
        "espacio",
        "colaboradores",
        "recursos",
        "compras",
        "prestacion",
        "anexo",
        "excepcion",
        "punto_entregas",
        "comedor",
    )
    operaciones = (
        Operacion(
            slug="reintentar_sync_gestionar",
            titulo="Reintentar envío a GESTIONAR",
            descripcion=(
                "Vuelve a enviar el alta del relevamiento a GESTIONAR. Solo para "
                "relevamientos no sincronizados; el envío es asincrónico."
            ),
            ejecutar=reintentar_sync_relevamiento,
            campo_estado="sincronizado_gestionar",
            icono="sync",
            # Uno por vez: los relevamientos previos a la migración 0010 figuran
            # sin sincronizar y cada reintento envía un "Add" a GESTIONAR.
            en_lote=False,
        ),
    )


@admin.register(PrimerSeguimiento)
class PrimerSeguimientoAdmin(OperacionesAdminMixin, SisocModelAdmin):
    list_display = (
        "id",
        "id_relevamiento",
        "tipo",
        "numero_orden",
        "estado",
        "estado_validacion",
        "fecha_hora",
        "sincronizado_gestionar",
        "origen",
    )
    list_select_related = ("id_relevamiento__comedor",)
    search_fields = (
        "=id",
        "=id_relevamiento__id",
        "id_relevamiento__comedor__nombre",
        "id_relevamiento__comedor__codigo_de_proyecto",
        "gestionar_id",
    )
    list_filter = (
        ("estado", ChoicesDropdownFilter),
        "tipo",
        ("estado_validacion", ChoicesDropdownFilter),
        "sincronizado_gestionar",
        "origen",
        ("fecha_hora", RangeDateTimeFilter),
    )
    raw_id_fields = (
        "id_relevamiento",
        "referente",
        "coordinador",
        "funcionamiento",
        "servicios_basicos",
        "almacenamiento_alimentos",
        "condiciones_higiene",
        "tareas_comedor",
        "recursos",
        "compras",
        "frecuencia_compra_alimentos",
        "menu",
        "registro_asistencia",
        "frecuencia_alimentos",
        "actividades_extras",
        "tarjeta",
        "rendicion_cuentas",
        "asistencia_tecnica",
        "cierre",
        "acta_excepcion",
    )
    operaciones = (
        Operacion(
            slug="reintentar_sync_gestionar",
            titulo="Reintentar envío a GESTIONAR",
            descripcion=(
                "Vuelve a enviar el alta del seguimiento a GESTIONAR. Solo para "
                "seguimientos no sincronizados; el envío es asincrónico."
            ),
            ejecutar=reintentar_sync_primer_seguimiento,
            campo_estado="sincronizado_gestionar",
            icono="sync",
            en_lote=False,
        ),
    )


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
