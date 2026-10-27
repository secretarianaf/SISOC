from django import forms
from django.conf import settings
from django.contrib import admin
from django.core.exceptions import ValidationError
from django.db import transaction
from unfold.contrib.filters.admin import (
    FieldTextFilter,
    RangeDateFilter,
    RangeDateTimeFilter,
    RelatedDropdownFilter,
)

from core.admin_base import SisocModelAdmin, SoloLecturaAdminMixin
from core.admin_operaciones import Operacion, OperacionesAdminMixin
from core.models import MontoPrestacionPrograma
from core.resources import MontoPrestacionProgramaResource

from core.admin_import_export import BaseExportAdmin, BaseImportExportAdmin
from comedores.models import (
    CapacitacionComedorCertificado,
    ComedorDatosConvenioPnud,
    ColaboradorEspacio,
    Comedor,
    EstadoDetalle,
    EstadoHistorial,
    EstadoProceso,
    HistorialValidacion,
    ImagenComedor,
    Nomina,
    NominaDerivacion,
    Observacion,
    Programas,
    Referente,
    TerritorialSyncLog,
    TipoDeComedor,
    ValorComida,
)
from comedores.services.colaborador_espacio_service import ColaboradorEspacioService
from comedores.services.estado_manager import registrar_cambio_estado
from comedores.services.validacion_service import ValidacionService
from comedores.tasks import AsyncSendComedorToGestionar, build_comedor_payload
from pwa.services.nomina_service import soft_delete_nomina_persona


# --- Operaciones de Comedor -------------------------------------------------


class SubestadoChoiceField(forms.ModelChoiceField):
    """Subestado con su estado general, para no confundir homónimos."""

    def label_from_instance(self, obj):
        return f"{obj.estado_actividad} / {obj.estado}"


class MotivoEstadoChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        proceso = obj.estado_proceso
        return f"{proceso.estado_actividad} / {proceso.estado} / {obj.estado}"


def _campos_cambiar_estado():
    return {
        "subestado": SubestadoChoiceField(
            label="Estado general / subestado",
            queryset=EstadoProceso.objects.filter(
                estado_actividad__isnull=False
            ).select_related("estado_actividad"),
        ),
        "motivo_estado": MotivoEstadoChoiceField(
            label="Motivo del estado",
            required=False,
            queryset=EstadoDetalle.objects.select_related(
                "estado_proceso__estado_actividad"
            ),
        ),
    }


def cambiar_estado_comedor(comedor, usuario, datos):
    """Mismas reglas que ``ComedorForm.clean`` + ``_sync_estado_historial``."""
    proceso = datos["subestado"]
    detalle = datos.get("motivo_estado")
    if detalle and detalle.estado_proceso_id != proceso.id:
        raise ValidationError(
            "El motivo seleccionado no pertenece al subestado elegido."
        )
    ultimo = comedor.ultimo_estado
    estado_actual = (
        (
            ultimo.estado_general.estado_actividad_id,
            ultimo.estado_general.estado_proceso_id,
            ultimo.estado_general.estado_detalle_id,
        )
        if ultimo
        else None
    )
    estado_nuevo = (
        proceso.estado_actividad_id,
        proceso.id,
        detalle.id if detalle else None,
    )
    if estado_actual == estado_nuevo:
        raise ValidationError("El comedor ya tiene ese estado.")
    return registrar_cambio_estado(
        comedor=comedor,
        actividad=proceso.estado_actividad,
        proceso=proceso,
        detalle=detalle,
        usuario=usuario,
    )


def _resultado_validacion(resultado):
    exito, mensaje = resultado
    if not exito:
        raise ValidationError(mensaje)
    return resultado


def validar_comedor(comedor, usuario, datos):
    return _resultado_validacion(
        ValidacionService.validar_comedor(
            comedor_id=comedor.pk,
            user=usuario,
            accion="validar",
            comentario=datos.get("motivo", ""),
        )
    )


def no_validar_comedor(comedor, usuario, datos):
    return _resultado_validacion(
        ValidacionService.validar_comedor(
            comedor_id=comedor.pk,
            user=usuario,
            accion="no_validar",
            opciones=list(datos["opciones"]),
            comentario=datos.get("motivo", ""),
        )
    )


def reenviar_comedor_a_gestionar(comedor, _usuario, _datos):
    """Mismo envío que la señal ``post_save``: al confirmar la transacción."""
    if not getattr(settings, "GESTIONAR_INTEGRATION_ENABLED", False):
        raise ValidationError("La integración con GESTIONAR está deshabilitada.")
    payload = build_comedor_payload(comedor)
    transaction.on_commit(lambda: AsyncSendComedorToGestionar(payload).start())


OPERACIONES_COMEDOR = (
    Operacion(
        slug="cambiar_estado",
        titulo="Cambiar estado del comedor",
        descripcion="Registra un nuevo estado en el historial del comedor.",
        ejecutar=cambiar_estado_comedor,
        campo_estado="ultimo_estado",
        motivo_obligatorio=True,
        campos=_campos_cambiar_estado,
        icono="swap_horiz",
    ),
    Operacion(
        slug="validar",
        titulo="Validar comedor",
        ejecutar=validar_comedor,
        campo_estado="estado_validacion",
        icono="verified",
    ),
    Operacion(
        slug="no_validar",
        titulo="Marcar como no validado",
        descripcion=(
            "El motivo es obligatorio cuando la opción es 'Otros' y queda como "
            "comentario del historial de validación."
        ),
        ejecutar=no_validar_comedor,
        campo_estado="estado_validacion",
        campos=lambda: {
            "opciones": forms.MultipleChoiceField(
                label="Motivos de no validación",
                choices=HistorialValidacion.OPCIONES_NO_VALIDAR,
            )
        },
        icono="block",
    ),
    Operacion(
        slug="reenviar_gestionar",
        titulo="Reenviar a GESTIONAR",
        descripcion=(
            "Efecto externo: envía los datos actuales del comedor a la API de "
            "GESTIONAR (alta, con reintento como actualización). No cambia "
            "datos en SISOC."
        ),
        ejecutar=reenviar_comedor_a_gestionar,
        icono="sync",
    ),
)


@admin.register(Comedor)
class ComedorAdmin(OperacionesAdminMixin, SisocModelAdmin):
    operaciones = OPERACIONES_COMEDOR
    list_display = [
        "id",
        "nombre",
        "programa",
        "estado_validacion",
        "fecha_validado",
        "provincia",
        "municipio",
    ]
    list_select_related = ["programa", "provincia", "municipio"]
    list_filter = [
        "estado_validacion",
        ("programa", RelatedDropdownFilter),
        ("provincia", RelatedDropdownFilter),
        "ultimo_estado__estado_general__estado_actividad",
        ("fecha_validado", RangeDateTimeFilter),
        ("fecha_creacion", RangeDateTimeFilter),
    ]
    search_fields = ["nombre", "codigo_de_proyecto", "organizacion__nombre"]
    readonly_fields = ["fecha_validado", "mes_ejecucion"]
    raw_id_fields = (
        "organizacion",
        "proyecto",
        "provincia",
        "municipio",
        "localidad",
        "responsable_tarjeta_provincia",
        "responsable_tarjeta_municipio",
        "responsable_tarjeta_localidad",
        "dupla",
        "referente",
    )


@admin.register(HistorialValidacion)
class HistorialValidacionAdmin(SoloLecturaAdminMixin, SisocModelAdmin):
    list_display = ["comedor", "estado_validacion", "usuario", "fecha_validacion"]
    list_select_related = ["comedor", "usuario"]
    list_filter = ["estado_validacion", ("fecha_validacion", RangeDateTimeFilter)]
    search_fields = ["comedor__nombre", "usuario__username", "comentario"]
    readonly_fields = ["fecha_validacion"]


@admin.register(EstadoHistorial)
class EstadoHistorialAdmin(SoloLecturaAdminMixin, SisocModelAdmin):
    list_display = ["comedor", "estado_general", "usuario", "fecha_cambio"]
    list_select_related = [
        "comedor",
        "usuario",
        "estado_general__estado_actividad",
        "estado_general__estado_proceso",
        "estado_general__estado_detalle",
    ]
    list_filter = [
        "estado_general__estado_actividad",
        ("fecha_cambio", RangeDateTimeFilter),
    ]
    search_fields = ["comedor__nombre", "usuario__username"]


@admin.register(TerritorialSyncLog)
class TerritorialSyncLogAdmin(SoloLecturaAdminMixin, SisocModelAdmin):
    list_display = [
        "fecha",
        "exitoso",
        "territoriales_sincronizados",
        "comedor_id",
        "error_mensaje",
    ]
    list_filter = ["exitoso", ("fecha", RangeDateTimeFilter)]
    search_fields = ["error_mensaje"]


@admin.register(Observacion)
class ObservacionAdmin(SisocModelAdmin):
    list_display = ["id", "comedor", "observador", "fecha_visita"]
    list_select_related = ["comedor"]
    list_filter = [("fecha_visita", RangeDateTimeFilter)]
    search_fields = ["comedor__nombre", "observador", "observacion"]
    raw_id_fields = ("comedor",)


# --- Operaciones de Nómina --------------------------------------------------


def baja_nomina(nomina, usuario, _datos):
    return soft_delete_nomina_persona(nomina=nomina, actor=usuario)


@admin.register(Nomina)
class NominaAdmin(OperacionesAdminMixin, SisocModelAdmin):
    operaciones = (
        Operacion(
            slug="baja",
            titulo="Dar de baja de la nómina",
            descripcion=(
                "Pasa la persona a estado Baja, desactiva su perfil PWA y sus "
                "inscripciones a actividades."
            ),
            ejecutar=baja_nomina,
            campo_estado="estado",
            motivo_obligatorio=True,
            destructiva=True,
            icono="person_remove",
        ),
    )
    list_display = ["id", "ciudadano", "comedor", "admision", "estado", "fecha"]
    # ``Nomina.__str__`` usa el comedor de la admisión.
    list_select_related = ["ciudadano", "comedor", "admision__comedor"]
    list_filter = ["estado", ("fecha", RangeDateTimeFilter)]
    search_fields = [
        "ciudadano__documento",
        "ciudadano__apellido",
        "ciudadano__nombre",
        "comedor__nombre",
        "admision__comedor__nombre",
    ]
    raw_id_fields = ("admision", "ciudadano", "comedor")


@admin.register(Referente)
class ReferenteAdmin(SisocModelAdmin):
    list_display = ["id", "apellido", "nombre", "documento", "mail", "celular"]
    search_fields = ["apellido", "nombre", "documento", "mail"]


@admin.register(ImagenComedor)
class ImagenComedorAdmin(SisocModelAdmin):
    list_display = ["id", "comedor", "imagen"]
    list_select_related = ["comedor"]
    search_fields = ["comedor__nombre"]
    raw_id_fields = ("relevamiento", "seguimiento", "subido_por", "comedor")


@admin.register(TipoDeComedor)
class TipoDeComedorAdmin(BaseImportExportAdmin):
    list_display = ("id", "nombre")
    search_fields = ("nombre",)


# `Programas.usa_admision_para_nomina` cambia el flujo de nómina del comedor:
# se exporta para consulta, pero el alta/edición sigue siendo manual.
@admin.register(Programas)
class ProgramasAdmin(BaseExportAdmin):
    list_display = ("id", "nombre", "usa_admision_para_nomina")
    list_filter = ("usa_admision_para_nomina",)
    search_fields = ("nombre",)


# Valores de comida: impacto económico directo, solo exportación.
@admin.register(ValorComida)
class ValorComidaAdmin(BaseExportAdmin):
    list_display = ("id", "tipo", "valor", "fecha")
    list_filter = ("tipo", "fecha")


@admin.register(ComedorDatosConvenioPnud)
class ComedorDatosConvenioPnudAdmin(SisocModelAdmin):
    list_display = (
        "comedor",
        "nro_convenio",
        "monto_total_conveniado",
        "prestaciones_financiadas_mensuales",
        "personas_conveniadas",
        "actualizado_en",
    )
    list_select_related = ("comedor",)
    search_fields = ("comedor__nombre", "nro_convenio")
    raw_id_fields = ("comedor",)
    readonly_fields = ("actualizado_en",)


# --- Operaciones de colaboradores del espacio -------------------------------


def baja_colaborador_espacio(colaborador, usuario, _datos):
    # El service es idempotente con la baja ya hecha; el admin lo informa.
    if colaborador.fecha_baja:
        raise ValidationError("El colaborador ya se encuentra dado de baja.")
    resultado = ColaboradorEspacioService.soft_delete(
        colaborador=colaborador, actor=usuario
    )
    if not resultado.get("success"):
        raise ValidationError(resultado.get("message"))
    return resultado


@admin.register(ColaboradorEspacio)
class ColaboradorEspacioAdmin(OperacionesAdminMixin, SisocModelAdmin):
    operaciones = (
        Operacion(
            slug="baja",
            titulo="Dar de baja colaborador",
            ejecutar=baja_colaborador_espacio,
            campo_estado="fecha_baja",
            motivo_obligatorio=True,
            destructiva=True,
            icono="person_remove",
        ),
    )
    list_display = ("ciudadano", "comedor", "genero", "fecha_alta", "fecha_baja")
    # ``__str__`` del colaborador y del ciudadano se resuelven con el join.
    list_select_related = ("ciudadano", "comedor")
    list_filter = (
        "genero",
        ("fecha_alta", RangeDateFilter),
        ("fecha_baja", RangeDateFilter),
        ("comedor__nombre", FieldTextFilter),
    )
    search_fields = (
        "ciudadano__apellido",
        "ciudadano__nombre",
        "ciudadano__documento",
        "comedor__nombre",
    )
    raw_id_fields = ("comedor", "ciudadano", "creado_por", "modificado_por")
    readonly_fields = ("fecha_creado", "fecha_modificado")


@admin.register(NominaDerivacion)
class NominaDerivacionAdmin(SisocModelAdmin):
    list_display = (
        "id",
        "nomina_origen",
        "nomina_destino",
        "comedor_origen",
        "comedor_destino",
        "usuario",
        "fecha",
    )
    list_select_related = (
        "nomina_origen__ciudadano",
        "nomina_origen__comedor",
        "nomina_origen__admision__comedor",
        "nomina_destino__ciudadano",
        "nomina_destino__comedor",
        "nomina_destino__admision__comedor",
        "comedor_origen",
        "comedor_destino",
        "usuario",
    )
    list_filter = (("fecha", RangeDateTimeFilter),)
    search_fields = (
        "usuario__username",
        "comedor_origen__nombre",
        "comedor_destino__nombre",
    )
    readonly_fields = (
        "nomina_origen",
        "nomina_destino",
        "comedor_origen",
        "comedor_destino",
        "usuario",
        "fecha",
        "motivo",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(CapacitacionComedorCertificado)
class CapacitacionComedorCertificadoAdmin(SisocModelAdmin):
    list_display = (
        "comedor",
        "capacitacion",
        "estado",
        "fecha_presentacion",
        "fecha_revision",
    )
    list_select_related = ("comedor",)
    list_filter = (
        "estado",
        "capacitacion",
        ("fecha_presentacion", RangeDateTimeFilter),
    )
    search_fields = ("comedor__nombre",)
    raw_id_fields = ("comedor", "presentado_por", "revisado_por")
    readonly_fields = ("observacion", "creado", "modificado")


# Montos de prestación: impacto económico directo, solo exportación.
@admin.register(MontoPrestacionPrograma)
class MontoPrestacionProgramaAdmin(BaseExportAdmin):
    resource_classes = [MontoPrestacionProgramaResource]
    list_display = (
        "programa",
        "desayuno_valor",
        "almuerzo_valor",
        "merienda_valor",
        "cena_valor",
        "fecha_creacion",
    )
    list_select_related = ("programa",)
    list_filter = ("programa",)
    raw_id_fields = ("usuario_creador",)
    readonly_fields = ("fecha_creacion", "fecha_modificacion")
