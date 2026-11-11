"""
Constantes y helpers de modelos auditables.

La metadata vive en una única fuente para evitar drift entre:
- opciones/allowlist de vistas
- registro real en django-auditlog
"""

from dataclasses import dataclass
from functools import lru_cache
from importlib import import_module
from typing import Callable

from django.apps import apps
from django.contrib.auth import get_user_model
from django.core.exceptions import FieldDoesNotExist


def _import_model(dotted_path: str):
    module_path, class_name = dotted_path.rsplit(".", 1)
    module = import_module(module_path)
    return getattr(module, class_name)


@dataclass(frozen=True)
class TrackedModelDefinition:
    """Definición canónica de un modelo auditable."""

    label: str
    model_getter: Callable
    excluded_fields: tuple[str, ...] = ()
    optional_excluded_fields: tuple[str, ...] = ()
    # Si se informa, solo se auditan estos campos (allowlist en vez de denylist).
    included_fields: tuple[str, ...] = ()
    redact_object_repr: bool = False

    def get_model(self):
        return self.model_getter()

    def get_model_key(self):
        # Clave estática cuando existe: el visor filtra LogEntry por
        # (app_label, model_name) sin importar el modelo, que puede vivir en
        # otro backend (src/backends/config/backends.json) y no estar en este proceso.
        static_key = getattr(self.model_getter, "model_key", None)
        if static_key:
            return static_key
        model = self.get_model()
        return model._meta.app_label, model._meta.model_name

    def is_installed(self):
        """Si el modelo pertenece a una app instalada en este proceso."""
        static_key = getattr(self.model_getter, "model_key", None)
        return static_key is None or apps.is_installed(static_key[0])

    def get_excluded_fields(self):
        model = self.get_model()
        fields = list(self.excluded_fields)
        for field_name in self.optional_excluded_fields:
            try:
                model._meta.get_field(field_name)
            except FieldDoesNotExist:
                continue
            fields.append(field_name)
        return fields


def _model_getter(dotted_path: str):
    """Getter perezoso con la clave ``(app_label, model_name)`` precalculada.

    Asume que el app label es el paquete raíz, como en todos los modelos de
    esta lista.
    """
    module_path, class_name = dotted_path.rsplit(".", 1)

    def getter():
        return _import_model(dotted_path)

    getter.model_key = (module_path.split(".")[0], class_name.lower())
    return getter


@lru_cache(maxsize=1)
def get_tracked_model_definitions():
    """
    Devuelve la definición canónica de modelos auditables.
    """
    return (
        TrackedModelDefinition(
            label="Comedor",
            model_getter=_model_getter("comedores.models.Comedor"),
            excluded_fields=("fecha_creacion",),
        ),
        TrackedModelDefinition(
            label="Centro de Infancia",
            model_getter=_model_getter("centrodeinfancia.models.CentroDeInfancia"),
            excluded_fields=("fecha_creacion",),
        ),
        TrackedModelDefinition(
            label="Formulario CDI",
            model_getter=_model_getter("centrodeinfancia.models.FormularioCDI"),
            excluded_fields=("created_at", "updated_at"),
        ),
        TrackedModelDefinition(
            label="Nómina CDI",
            model_getter=_model_getter("centrodeinfancia.models.NominaCentroInfancia"),
            # La ficha tiene datos de salud de niños/as y el log es exportable y
            # sobrevive al borrado: solo se registra quién cambia los teléfonos,
            # que son los datos de contacto editables junto a la identidad
            # verificada por RENAPER.
            included_fields=(
                "responsable_legal_1_telefono",
                "responsable_legal_2_telefono",
                "adulto_responsable_telefono",
            ),
        ),
        TrackedModelDefinition(
            label="Trabajador CDI",
            model_getter=_model_getter("centrodeinfancia.models.Trabajador"),
            # Mismo criterio que "Nómina CDI": la ficha tiene datos sensibles,
            # se audita solo el contacto editable.
            included_fields=("telefono", "email"),
        ),
        TrackedModelDefinition(
            label="Acceso CDI",
            model_getter=_model_getter("centrodeinfancia.models.AccesoCDI"),
            excluded_fields=("fecha_creacion",),
        ),
        TrackedModelDefinition(
            label="Acceso CDF",
            model_getter=_model_getter("centrodefamilia.models.AccesoCDF"),
            excluded_fields=("fecha_creacion",),
        ),
        TrackedModelDefinition(
            label="Relevamiento",
            model_getter=_model_getter("relevamientos.models.Relevamiento"),
            excluded_fields=("fecha_creacion",),
        ),
        TrackedModelDefinition(
            label="Ciudadano",
            model_getter=_model_getter("ciudadanos.models.Ciudadano"),
            excluded_fields=("creado", "modificado"),
        ),
        TrackedModelDefinition(
            label="Nómina",
            model_getter=_model_getter("comedores.models.Nomina"),
            excluded_fields=("fecha",),
        ),
        TrackedModelDefinition(
            label="Organización",
            model_getter=_model_getter("organizaciones.models.Organizacion"),
            excluded_fields=("fecha_creacion",),
        ),
        TrackedModelDefinition(
            label="Usuario",
            model_getter=get_user_model,
            excluded_fields=("password",),
            optional_excluded_fields=("last_login",),
        ),
        TrackedModelDefinition(
            label="Encuesta",
            model_getter=_model_getter("encuestas.models.Encuesta"),
            excluded_fields=("fecha_creacion", "fecha_ultima_modificacion"),
        ),
        TrackedModelDefinition(
            label="Ronda de encuesta",
            model_getter=_model_getter("encuestas.models.RondaEncuesta"),
        ),
        TrackedModelDefinition(
            label="Relevamiento DataCalle",
            model_getter=_model_getter("datacalle.models.Relevamiento"),
            # Mismo motivo que en "Caso DataCalle": el log es exportable y
            # sobrevive al borrado. `cerrar_relevamiento` completa estos
            # campos en cada cierre de operativo, y son más sensibles que un
            # caso individual porque describen a todo un grupo en un punto
            # exacto: `lat`/`lon` (coordenadas GPS del cierre) y
            # `observacion_asentamiento`/`otra_observacion` (cómo vive el
            # grupo ahí, la segunda en texto libre). `area_operativa` no se
            # excluye a propósito: es dato de planificación que escribe el
            # coordinador, es la identidad del operativo (la property
            # `lugar` la expone) y es justo uno de los campos cuyos cambios
            # tiene sentido rastrear.
            excluded_fields=(
                "lat",
                "lon",
                "observacion_asentamiento",
                "otra_observacion",
            ),
        ),
        TrackedModelDefinition(
            label="Caso DataCalle",
            model_getter=_model_getter("datacalle.models.Encuesta"),
            # El log de auditoría es exportable (audittrail/views.py) y
            # sobrevive al borrado (soft delete) del caso, así que no puede
            # llevar ni el instrumento completo ni los datos que identifican
            # o ubican a una persona en situación de calle: ni `respuestas`
            # (el JSON crudo del cuestionario), ni las columnas indexadas
            # que `_copiar_columnas_indexadas` saca de ese mismo instrumento
            # y que son igual de sensibles (`lat`/`lon`: ubicación exacta
            # donde se la encontró; `codigo_entrevistado`: su identificador;
            # `persona_entrevistada`: franja etaria y de género;
            # `es_menor_de_edad`). Lo que 8.6 pide auditar es que el caso
            # cambió, cuándo y quién lo cambió — para eso alcanza con
            # `estado`, `relevamiento`, `origen`, `variante`, `grupo_id`,
            # `es_cabecera_grupo`, `lugar_hallazgo`, `realiza_entrevista`,
            # `personas_observadas` y los timestamps, que sí quedan.
            excluded_fields=(
                "respuestas",
                "lat",
                "lon",
                "codigo_entrevistado",
                "persona_entrevistada",
                "es_menor_de_edad",
            ),
        ),
        # VAT: lo que define quién accede a formación y con qué resultado.
        # Los `fecha_modificacion` (auto_now) se excluyen porque cambian en
        # cada guardado y llenarían el log de ruido. Las `observaciones` de
        # alumnos son texto libre sobre personas y el log es exportable y
        # sobrevive al borrado: se audita el cambio de estado o nota, no la
        # nota libre.
        TrackedModelDefinition(
            label="Centro VAT",
            model_getter=_model_getter("VAT.models.Centro"),
        ),
        TrackedModelDefinition(
            label="Inscripción VAT",
            model_getter=_model_getter("VAT.models.Inscripcion"),
            excluded_fields=(
                "fecha_creacion",
                "fecha_modificacion",
                "observaciones",
            ),
        ),
        TrackedModelDefinition(
            label="Parametría de voucher VAT",
            model_getter=_model_getter("VAT.models.VoucherParametria"),
            excluded_fields=("fecha_creacion",),
        ),
        TrackedModelDefinition(
            label="Voucher VAT",
            model_getter=_model_getter("VAT.models.Voucher"),
            excluded_fields=("fecha_creacion", "fecha_modificacion"),
        ),
        TrackedModelDefinition(
            label="Resultado de evaluación VAT",
            model_getter=_model_getter("VAT.models.ResultadoEvaluacion"),
            excluded_fields=(
                "fecha_creacion",
                "fecha_modificacion",
                "observaciones",
            ),
        ),
        TrackedModelDefinition(
            label="Acta de cierre VAT",
            model_getter=_model_getter("VAT.models.ActaCierreComision"),
            excluded_fields=("fecha_creacion", "fecha_modificacion"),
        ),
        # Celiaquía: el expediente provincial, las decisiones sobre cada
        # legajo, el cupo de cada provincia, el técnico asignado y los pagos.
        TrackedModelDefinition(
            label="Expediente Celiaquía",
            model_getter=_model_getter("celiaquia.models.Expediente"),
            excluded_fields=(
                "fecha_creacion",
                "fecha_modificacion",
                "observaciones",
            ),
        ),
        TrackedModelDefinition(
            label="Legajo Celiaquía",
            redact_object_repr=True,
            model_getter=_model_getter("celiaquia.models.ExpedienteCiudadano"),
            # Estar en el legajo ya es un dato de salud y el log es exportable
            # y sobrevive al borrado: solo se registran las decisiones del
            # circuito, sin los motivos en texto libre ni los archivos.
            included_fields=(
                "estado",
                "rol",
                "archivos_ok",
                "revision_tecnico",
                "resultado_sintys",
                "cruce_ok",
                "estado_cupo",
                "es_titular_activo",
                "estado_validacion_renaper",
            ),
        ),
        TrackedModelDefinition(
            label="Cupo provincial Celiaquía",
            model_getter=_model_getter("celiaquia.models.ProvinciaCupo"),
        ),
        TrackedModelDefinition(
            label="Asignación de técnico Celiaquía",
            model_getter=_model_getter("celiaquia.models.AsignacionTecnico"),
            excluded_fields=("fecha_asignacion",),
        ),
        TrackedModelDefinition(
            label="Pago Celiaquía",
            model_getter=_model_getter("celiaquia.models.PagoExpediente"),
            excluded_fields=("creado_en", "modificado_en"),
        ),
        # PAS: estado y datos de contacto de cada titular (mismo criterio que
        # "Ciudadano"), el circuito mensual con SINTYS y las incompatibilidades
        # detectadas. Los avisos (M2M) ya quedan en `PasHistorialEstado`.
        TrackedModelDefinition(
            label="Persona PAS",
            model_getter=_model_getter("pas.models.PasPersona"),
            excluded_fields=("fecha_creacion", "fecha_actualizacion"),
        ),
        TrackedModelDefinition(
            label="Circuito mensual PAS",
            model_getter=_model_getter("pas.models.PasCircuitoMensual"),
        ),
        TrackedModelDefinition(
            label="Incompatibilidad PAS",
            model_getter=_model_getter("pas.models.PasIncompatibilidad"),
            excluded_fields=("fecha_deteccion",),
        ),
        # VPSL: el circuito del operativo (itinerario, sedes, jornadas, cierre)
        # y el seguimiento de cada atención y su caso de laboratorio.
        TrackedModelDefinition(
            label="Itinerario VPSL",
            model_getter=_model_getter("ver_para_ser_libre.models.ItinerarioVPSL"),
            excluded_fields=("created_at", "updated_at"),
        ),
        TrackedModelDefinition(
            label="Evaluación de sede VPSL",
            model_getter=_model_getter(
                "ver_para_ser_libre.models.EvaluacionSedeItinerarioVPSL"
            ),
            excluded_fields=("updated_at",),
        ),
        TrackedModelDefinition(
            label="Sede VPSL",
            model_getter=_model_getter("ver_para_ser_libre.models.SedeVPSL"),
        ),
        TrackedModelDefinition(
            label="Jornada VPSL",
            model_getter=_model_getter("ver_para_ser_libre.models.JornadaVPSL"),
            # La respuesta cruda de RENAPER del referente no va al log.
            excluded_fields=("created_at", "updated_at", "referente_datos_renaper"),
        ),
        TrackedModelDefinition(
            label="Registro nominal VPSL",
            redact_object_repr=True,
            model_getter=_model_getter("ver_para_ser_libre.models.RegistroNominalVPSL"),
            # Atención oftalmológica de chicos y chicas: resultado, graduación,
            # prescripción y datos personales son de salud y el log es
            # exportable y sobrevive al borrado. Solo se registra el circuito
            # administrativo del registro.
            included_fields=(
                "estado",
                "numero_acta",
                "numero_sobre",
                "validado_renaper",
                "no_verificar_renaper",
            ),
        ),
        TrackedModelDefinition(
            label="Caso de laboratorio VPSL",
            redact_object_repr=True,
            model_getter=_model_getter("ver_para_ser_libre.models.CasoLaboratorioVPSL"),
            # `destinatario` e `incidencia` son texto libre sobre la persona.
            excluded_fields=("updated_at", "destinatario", "incidencia"),
        ),
        TrackedModelDefinition(
            label="Cierre diario VPSL",
            model_getter=_model_getter("ver_para_ser_libre.models.CierreDiarioVPSL"),
        ),
        # Comedores - fondos: pagos, rendiciones mensuales y finales, y la
        # revisión de cada documento. Son datos institucionales, no personales.
        TrackedModelDefinition(
            label="Expediente de pago",
            model_getter=_model_getter("expedientespagos.models.ExpedientePago"),
            excluded_fields=("fecha_creacion",),
        ),
        TrackedModelDefinition(
            label="Rendición de cuentas mensual",
            model_getter=_model_getter(
                "rendicioncuentasmensual.models.RendicionCuentaMensual"
            ),
            # `usuario_ultima_modificacion` repite al actor del evento.
            excluded_fields=(
                "fecha_creacion",
                "ultima_modificacion",
                "usuario_ultima_modificacion",
            ),
        ),
        TrackedModelDefinition(
            label="Documento de rendición mensual",
            model_getter=_model_getter(
                "rendicioncuentasmensual.models.DocumentacionAdjunta"
            ),
            # Las marcas de "visto" cambian con cada apertura: son ruido.
            excluded_fields=(
                "fecha_creacion",
                "ultima_modificacion",
                "visualizacion_etapa",
                "visualizacion_usuario",
                "visualizacion_fecha",
            ),
        ),
        TrackedModelDefinition(
            label="Solicitud de documento faltante",
            model_getter=_model_getter(
                "rendicioncuentasmensual.models.SolicitudDocumentoFaltante"
            ),
            excluded_fields=("fecha_creacion",),
        ),
        TrackedModelDefinition(
            label="Rendición de cuentas final",
            model_getter=_model_getter(
                "rendicioncuentasfinal.models.RendicionCuentasFinal"
            ),
        ),
        TrackedModelDefinition(
            label="Documento de rendición final",
            model_getter=_model_getter(
                "rendicioncuentasfinal.models.DocumentoRendicionFinal"
            ),
            excluded_fields=("fecha_modificacion",),
        ),
        # Comedores - circuito de admisión y acompañamiento. `AdmisionHistorial`
        # ya guarda algunos campos de la admisión, pero no se ve en el visor.
        TrackedModelDefinition(
            label="Admisión",
            model_getter=_model_getter("admisiones.models.admisiones.Admision"),
            # El snapshot es una copia JSON de la organización que se reescribe
            # con `.update()`; `creado`/`modificado` cambian solos.
            excluded_fields=("creado", "modificado", "datos_organizacion_snapshot"),
        ),
        TrackedModelDefinition(
            label="Documento de admisión",
            model_getter=_model_getter("admisiones.models.admisiones.ArchivoAdmision"),
            excluded_fields=("creado", "modificado", "modificado_por"),
        ),
        TrackedModelDefinition(
            label="Informe técnico de admisión",
            model_getter=_model_getter("admisiones.models.admisiones.InformeTecnico"),
            # El informe copia DNI y datos del representante y del responsable
            # de la tarjeta: solo se registra su avance y lo que se convenia.
            included_fields=(
                "estado",
                "estado_formulario",
                "tipo",
                "monto_total_conveniado",
                "total_acreditaciones",
                "plazo_ejecucion",
            ),
        ),
        TrackedModelDefinition(
            label="Informe complementario de admisión",
            model_getter=_model_getter(
                "admisiones.models.admisiones.InformeComplementario"
            ),
            excluded_fields=("creado", "modificado"),
        ),
        TrackedModelDefinition(
            label="Acompañamiento",
            model_getter=_model_getter(
                "acompanamientos.models.acompanamiento.Acompanamiento"
            ),
            excluded_fields=("fecha_creacion",),
        ),
        TrackedModelDefinition(
            label="Información relevante de acompañamiento",
            model_getter=_model_getter(
                "acompanamientos.models.acompanamiento.InformacionRelevante"
            ),
            excluded_fields=("fecha_creacion",),
        ),
        TrackedModelDefinition(
            label="Prestación de acompañamiento",
            model_getter=_model_getter(
                "acompanamientos.models.acompanamiento.Prestacion"
            ),
        ),
        TrackedModelDefinition(
            label="Hitos de acompañamiento",
            model_getter=_model_getter("acompanamientos.models.hitos.Hitos"),
        ),
        TrackedModelDefinition(
            label="Dupla",
            model_getter=_model_getter("duplas.models.Dupla"),
            # Los técnicos son M2M: la lista única todavía no los registra.
            excluded_fields=("fecha",),
        ),
        # Comedores - datos del convenio, certificaciones y valores.
        TrackedModelDefinition(
            label="Datos de convenio PNUD del comedor",
            model_getter=_model_getter("comedores.models.ComedorDatosConvenioPnud"),
            excluded_fields=("actualizado_en",),
        ),
        TrackedModelDefinition(
            label="Certificado de capacitación del comedor",
            model_getter=_model_getter(
                "comedores.models.CapacitacionComedorCertificado"
            ),
            excluded_fields=("creado", "modificado"),
        ),
        TrackedModelDefinition(
            label="Conformidad de prestación alimentaria",
            model_getter=_model_getter(
                "comedores.models.PrestacionAlimentariaConformidad"
            ),
            excluded_fields=("creado", "dni_certificador"),
        ),
        TrackedModelDefinition(
            label="Valor de comida",
            model_getter=_model_getter("comedores.models.ValorComida"),
        ),
        # Comedores - seguimientos y su validación por coordinación.
        TrackedModelDefinition(
            label="Primer seguimiento",
            model_getter=_model_getter("relevamientos.models.PrimerSeguimiento"),
        ),
        TrackedModelDefinition(
            label="Seguimiento PNUD",
            model_getter=_model_getter("relevamientos.models.SeguimientoPnud"),
            # `datos` es el formulario completo en JSON.
            excluded_fields=("fecha_creacion", "fecha_actualizacion", "datos"),
        ),
        TrackedModelDefinition(
            label="Acta complementaria",
            model_getter=_model_getter("relevamientos.models.ActaComplementaria"),
            excluded_fields=("fecha_creacion",),
        ),
        TrackedModelDefinition(
            label="Comunicado",
            model_getter=_model_getter("comunicados.models.Comunicado"),
            excluded_fields=(
                "fecha_creacion",
                "fecha_ultima_modificacion",
                "usuario_ultima_modificacion",
            ),
        ),
        # Organizaciones: proyectos y documentación presentada.
        TrackedModelDefinition(
            label="Proyecto de organización",
            model_getter=_model_getter("organizaciones.models.ProyectoOrganizacion"),
        ),
        TrackedModelDefinition(
            label="Documento de organización",
            model_getter=_model_getter("organizaciones.models.ArchivoOrganizacion"),
            excluded_fields=("creado", "modificado", "modificado_por"),
        ),
        # Centros de Familia.
        TrackedModelDefinition(
            label="Centro de Familia",
            model_getter=_model_getter("centrodefamilia.models.Centro"),
        ),
        TrackedModelDefinition(
            label="Actividad de Centro de Familia",
            model_getter=_model_getter("centrodefamilia.models.ActividadCentro"),
        ),
        TrackedModelDefinition(
            label="Participante de actividad CDF",
            model_getter=_model_getter("centrodefamilia.models.ParticipanteActividad"),
            excluded_fields=("fecha_registro", "fecha_modificacion"),
        ),
        TrackedModelDefinition(
            label="Dispositivo",
            model_getter=_model_getter("dispositivos.models.Dispositivo"),
            excluded_fields=("created_at", "updated_at"),
        ),
        # Configuración: programas, montos, catálogos, insumos y tableros.
        TrackedModelDefinition(
            label="Programa",
            model_getter=_model_getter("core.models.Programa"),
        ),
        TrackedModelDefinition(
            label="Monto de prestación por programa",
            model_getter=_model_getter("core.models.MontoPrestacionPrograma"),
            excluded_fields=("fecha_creacion", "fecha_modificacion"),
        ),
        TrackedModelDefinition(
            label="Tipo de intervención",
            model_getter=_model_getter(
                "catalogo_intervenciones.models.TipoIntervencion"
            ),
        ),
        TrackedModelDefinition(
            label="Subintervención",
            model_getter=_model_getter(
                "catalogo_intervenciones.models.SubIntervencion"
            ),
        ),
        TrackedModelDefinition(
            label="Categoría de insumo",
            model_getter=_model_getter("insumos.models.InsumoCategoria"),
            excluded_fields=("fecha_creacion", "fecha_actualizacion"),
        ),
        TrackedModelDefinition(
            label="Insumo",
            model_getter=_model_getter("insumos.models.Insumo"),
            excluded_fields=(
                "fecha_creacion",
                "fecha_actualizacion",
                "usuario_actualizacion",
            ),
        ),
        TrackedModelDefinition(
            label="Tablero",
            model_getter=_model_getter("dashboard.models.Tablero"),
        ),
    )


def get_tracked_models():
    """
    Lista de tuplas (app_label, model_name, label) para UI/allowlist.
    """
    return [
        (*definition.get_model_key(), definition.label)
        for definition in get_tracked_model_definitions()
    ]


def get_tracked_model_allowlist():
    """
    Mapa (app_label, model_name) -> definición.
    """
    return {
        definition.get_model_key(): definition
        for definition in get_tracked_model_definitions()
    }


def is_tracked_model(app_label: str, model_name: str) -> bool:
    """
    Verifica si un par app/model está habilitado para auditoría.
    """
    return (app_label, model_name) in get_tracked_model_allowlist()


# Compatibilidad hacia atrás: código/tests existentes importan TRACKED_MODELS.
TRACKED_MODELS = get_tracked_models()


def tracked_model_choices(include_blank: bool = True):
    """
    Devuelve choices listos para formularios (app.model -> etiqueta amigable).
    """
    choices = []
    if include_blank:
        choices.append(("", "Todos los modelos"))
    choices.extend(
        (f"{app}.{model}", label) for app, model, label in get_tracked_models()
    )
    return choices
