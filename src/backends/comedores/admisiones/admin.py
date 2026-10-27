from django.contrib import admin
from django.core.exceptions import ValidationError
from unfold.contrib.filters.admin import (
    ChoicesDropdownFilter,
    RangeDateFilter,
    RangeDateTimeFilter,
)

from acompanamientos.acompanamiento_service import AcompanamientoService
from core.admin_base import SisocModelAdmin, SoloLecturaAdmin
from core.admin_import_export import BaseExportAdmin
from core.admin_operaciones import Operacion, OperacionesAdminMixin
from admisiones.services.admisiones_service.impl import AdmisionService
from admisiones.models.admisiones import (
    EstadoAdmision,
    TipoConvenio,
    Admision,
    Documentacion,
    ArchivoAdmision,
    InformeTecnico,
    InformeTecnicoPDF,
    AdmisionHistorial,
    HistorialEstadosAdmision,
    FormularioProyectoDisposicion,
    Providencia,
    FormularioProyectoDeConvenio,
    DocumentosExpediente,
    IncidenciaTemplateInformeTecnico,
    IncidenciaTemplateInformeTecnicoCaso,
    PlantillaInformeTecnico,
    PlantillaInformeTecnicoVersion,
    PlantillaInformeTecnicoPublicacion,
    VariableTemplateInformeTecnico,
)


# Operaciones de soporte (issue #2789). Cada adaptador repite la secuencia que
# arma AdmisionService._procesar_post_* para el botón equivalente de la
# pantalla, y antes valida la misma condición con la que la pantalla muestra
# ese botón (AdmisionService._append_botones_*).


def enviar_a_legales(admision, usuario, _datos):
    if admision.estado_admision != "if_informe_tecnico_cargado":
        raise ValidationError(
            "Solo se envía a legales con el IF del informe técnico cargado."
        )
    if not AdmisionService.marcar_como_enviado_a_legales(admision, usuario):
        return False
    AdmisionService.actualizar_estado_admision(admision, "enviar_a_legales")
    return True


def enviar_a_acompaniamiento(admision, usuario, _datos):
    if not admision.numero_convenio or admision.enviado_acompaniamiento:
        raise ValidationError(
            "Solo se envía a acompañamiento con número de convenio y si no fue "
            "enviada antes."
        )
    AcompanamientoService.importar_datos_desde_admision(admision)
    if not AdmisionService.marcar_como_enviado_a_acompaniamiento(admision, usuario):
        return False
    if not AdmisionService.actualizar_estado_admision(
        admision, "enviar_a_acompaniamiento"
    ):
        raise ValidationError(
            "No se pudo actualizar el estado de la admisión a acompañamiento."
        )
    return True


def marcar_documentacion_rectificada(admision, usuario, _datos):
    if admision.estado_legales != "A Rectificar":
        raise ValidationError(
            "Solo se rectifica documentación de admisiones en estado 'A Rectificar'."
        )
    return AdmisionService.marcar_como_documentacion_rectificada(admision, usuario)


# EstadoAdmision y TipoConvenio se resuelven por nombre dentro de los servicios
# de admisiones (ej. EstadoAdmision.objects.get(nombre=...)): renombrarlos en
# lote rompería el flujo de estados, por eso solo se habilita exportación.
@admin.register(EstadoAdmision)
class EstadoAdmisionAdmin(BaseExportAdmin):
    list_display = ("id", "nombre")
    search_fields = ("nombre",)


@admin.register(TipoConvenio)
class TipoConvenioAdmin(BaseExportAdmin):
    list_display = ("id", "nombre")
    search_fields = ("nombre",)


@admin.register(Admision)
class AdmisionAdmin(OperacionesAdminMixin, SisocModelAdmin):
    list_display = (
        "id",
        "comedor",
        "tipo",
        "estado",
        "estado_admision",
        "estado_legales",
        "num_expediente",
        "activa",
        "creado",
    )
    list_select_related = ("comedor", "estado")
    search_fields = (
        "=id",
        "comedor__nombre",
        "comedor__codigo_de_proyecto",
        "num_expediente",
        "numero_convenio",
    )
    list_filter = (
        ("estado_admision", ChoicesDropdownFilter),
        ("estado_legales", ChoicesDropdownFilter),
        "tipo",
        "activa",
        "enviado_legales",
        "enviado_acompaniamiento",
        ("creado", RangeDateFilter),
    )
    raw_id_fields = ("comedor",)
    operaciones = (
        Operacion(
            slug="enviar_legales",
            titulo="Enviar a legales",
            descripcion=(
                "Marca la admisión como enviada a legales. Requiere el IF del "
                "informe técnico cargado."
            ),
            ejecutar=enviar_a_legales,
            campo_estado="estado_admision",
            icono="gavel",
        ),
        Operacion(
            slug="enviar_acompaniamiento",
            titulo="Enviar a acompañamiento",
            descripcion=(
                "Crea el acompañamiento con los datos de la admisión y la marca "
                "como enviada. Requiere número de convenio."
            ),
            ejecutar=enviar_a_acompaniamiento,
            campo_estado="estado_admision",
            en_lote=False,
            icono="handshake",
        ),
        Operacion(
            slug="documentacion_rectificada",
            titulo="Marcar documentación rectificada",
            descripcion=(
                "Vuelve a enviar a legales una admisión en 'A Rectificar' y limpia "
                "sus observaciones."
            ),
            ejecutar=marcar_documentacion_rectificada,
            campo_estado="estado_legales",
            icono="task_alt",
        ),
    )


@admin.register(Documentacion)
class DocumentacionAdmin(SisocModelAdmin):
    list_display = ("id", "nombre", "obligatorio", "orden")
    list_filter = ("obligatorio", "convenios")
    search_fields = ("nombre",)


@admin.register(ArchivoAdmision)
class ArchivoAdmisionAdmin(SisocModelAdmin):
    list_display = ("id", "admision", "documentacion", "estado", "num_if", "creado")
    list_select_related = ("admision__comedor", "documentacion")
    search_fields = ("=admision__id", "admision__comedor__nombre", "num_if")
    list_filter = (
        ("estado", ChoicesDropdownFilter),
        ("creado", RangeDateFilter),
    )
    raw_id_fields = (
        "admision",
        "archivo_organizacion_origen",
        "creado_por",
        "modificado_por",
    )


@admin.register(InformeTecnico)
class InformeTecnicoAdmin(SisocModelAdmin):
    list_display = (
        "id",
        "admision",
        "expediente_nro",
        "nombre_organizacion",
        "tipo",
        "estado",
        "estado_formulario",
        "creado",
    )
    list_select_related = ("admision__comedor",)
    search_fields = (
        "=id",
        "=admision__id",
        "expediente_nro",
        "nombre_organizacion",
        "cuit_organizacion",
        "nombre_espacio",
    )
    list_filter = (
        ("estado", ChoicesDropdownFilter),
        "tipo",
        "estado_formulario",
        ("creado", RangeDateFilter),
    )
    raw_id_fields = ("admision", "creado_por", "modificado_por")


@admin.register(InformeTecnicoPDF)
class InformeTecnicoPDFAdmin(SisocModelAdmin):
    list_display = ("id", "admision", "comedor", "tipo", "creado")
    list_select_related = ("admision__comedor", "comedor")
    search_fields = ("=admision__id", "comedor__nombre")
    list_filter = ("tipo", ("creado", RangeDateTimeFilter))
    raw_id_fields = ("admision", "comedor")


@admin.register(AdmisionHistorial)
class AdmisionHistorialAdmin(SoloLecturaAdmin):
    list_display = ("id", "admision", "campo", "usuario", "fecha")
    list_select_related = ("admision__comedor", "usuario")
    search_fields = ("=admision__id", "campo", "usuario__username")
    list_filter = (("fecha", RangeDateTimeFilter),)


@admin.register(HistorialEstadosAdmision)
class HistorialEstadosAdmisionAdmin(SoloLecturaAdmin):
    list_display = (
        "id",
        "admision",
        "estado_anterior",
        "estado_nuevo",
        "usuario",
        "fecha",
    )
    list_select_related = ("admision__comedor", "usuario")
    search_fields = ("=admision__id", "admision__comedor__nombre", "estado_nuevo")
    list_filter = ("estado_nuevo", ("fecha", RangeDateTimeFilter))


@admin.register(FormularioProyectoDisposicion)
class FormularioProyectoDisposicionAdmin(SisocModelAdmin):
    list_display = ("id", "admision", "tipo", "numero_if", "creado")
    list_select_related = ("admision__comedor",)
    search_fields = ("=admision__id", "numero_if")
    list_filter = ("tipo", ("creado", RangeDateTimeFilter))
    raw_id_fields = ("admision", "creado_por")


@admin.register(Providencia)
class ProvidenciaAdmin(SisocModelAdmin):
    list_display = ("id", "admision", "orden", "tipo", "numero_gde_pv", "creado")
    list_select_related = ("admision__comedor",)
    search_fields = ("=admision__id", "numero_gde_pv", "numero_pv_primera")
    list_filter = ("orden", ("creado", RangeDateTimeFilter))
    raw_id_fields = ("admision", "creado_por")


@admin.register(FormularioProyectoDeConvenio)
class FormularioProyectoDeConvenioAdmin(SisocModelAdmin):
    list_display = ("id", "admision", "numero_if", "creado")
    list_select_related = ("admision__comedor",)
    search_fields = ("=admision__id", "numero_if")
    list_filter = (("creado", RangeDateTimeFilter),)
    raw_id_fields = ("admision", "creado_por")


@admin.register(DocumentosExpediente)
class DocumentosExpedienteAdmin(SisocModelAdmin):
    list_display = ("id", "admision", "nombre", "tipo", "num_if", "creado")
    list_select_related = ("admision",)
    search_fields = ("=admision__id", "nombre", "num_if")
    list_filter = ("rectificar", ("creado", RangeDateFilter))
    raw_id_fields = ("admision",)


@admin.register(PlantillaInformeTecnico)
class PlantillaInformeTecnicoAdmin(BaseExportAdmin):
    list_display = ("codigo", "nombre", "tipo_admision", "tipo_convenio", "estado")
    list_filter = ("tipo_admision", "estado", "tipo_convenio")
    search_fields = ("codigo", "nombre")
    readonly_fields = ("codigo", "creado", "modificado")

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = super().get_readonly_fields(request, obj)
        if obj is None:
            return readonly_fields
        return (
            *readonly_fields,
            "tipo_admision",
            "tipo_convenio",
            "es_ex_pnud",
            "estado_convenio_pnud",
            "tipo_renovacion",
            "estado_financiamiento",
        )


@admin.register(PlantillaInformeTecnicoVersion)
class PlantillaInformeTecnicoVersionAdmin(BaseExportAdmin):
    list_display = ("plantilla", "numero", "estado", "creado", "publicado")
    list_filter = ("estado",)
    search_fields = ("plantilla__codigo", "plantilla__nombre")
    readonly_fields = ("creado", "modificado", "publicado")

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = super().get_readonly_fields(request, obj)
        if obj is None or obj.estado == "borrador":
            return readonly_fields
        return (
            *readonly_fields,
            "plantilla",
            "numero",
            "contenido_html",
            "observaciones",
            "estado",
            "creado_por",
            "publicado_por",
        )


@admin.register(PlantillaInformeTecnicoPublicacion)
class PlantillaInformeTecnicoPublicacionAdmin(BaseExportAdmin):
    list_display = ("plantilla", "version", "publicada", "publicada_por")
    search_fields = ("plantilla__codigo", "plantilla__nombre", "clave_condiciones")
    readonly_fields = ("clave_condiciones", "publicada", "publicada_por")


@admin.register(VariableTemplateInformeTecnico)
class VariableTemplateInformeTecnicoAdmin(BaseExportAdmin):
    list_display = ("nombre", "categoria", "codigo", "activo", "orden")
    list_filter = ("activo", "categoria")
    search_fields = ("nombre", "codigo", "descripcion")
    ordering = ("categoria", "orden", "nombre")


@admin.register(IncidenciaTemplateInformeTecnico)
class IncidenciaTemplateInformeTecnicoAdmin(BaseExportAdmin):
    list_display = (
        "codigo",
        "estado",
        "cantidad_casos",
        "plantilla",
        "ultima_fecha",
    )
    list_filter = ("estado",)
    search_fields = ("codigo", "clave_condiciones")
    readonly_fields = (
        "codigo",
        "clave_condiciones",
        "clave_abierta",
        "condiciones",
        "cantidad_casos",
        "primera_fecha",
        "ultima_fecha",
    )


@admin.register(IncidenciaTemplateInformeTecnicoCaso)
class IncidenciaTemplateInformeTecnicoCasoAdmin(BaseExportAdmin):
    list_display = (
        "incidencia",
        "admision_id_reportada",
        "informe_id_reportado",
        "comedor_nombre",
        "creado",
    )
    search_fields = (
        "incidencia__codigo",
        "comedor_nombre",
        "organizacion_nombre",
    )
    readonly_fields = (
        "incidencia",
        "referencia_caso",
        "admision",
        "admision_id_reportada",
        "informe",
        "informe_id_reportado",
        "comedor_nombre",
        "organizacion_nombre",
        "programa_nombre",
        "estado_admision",
        "detalle",
        "reportado_por",
        "creado",
        "modificado",
    )
