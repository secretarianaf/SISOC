"""Diagnóstico (y reparación opcional) de los datos que dañó la app el 28/9/2026.

Caso 1, app 1.1.44 (envíos de ~21:17 a ~21:31 UTC): la pregunta 2.1.6 del
seguimiento PAC ("los elementos de limpieza, ¿se encuentran guardados en el
mismo lugar que los alimentos?") viajó directo a
``ServiciosBasicosSeguimiento.elementos_guardados``, que en SISOC significa lo
contrario ("¿correctamente guardados?"). La 1.1.45 lo corrigió.

Caso 2, app 1.1.45 (envíos de ~21:31 a ~21:58 UTC): el seguimiento PAC mandaba
``''`` en todo campo visible sin responder y ``PrimerSeguimientoSerializer`` lo
guarda como ``None`` (``partial=True``). En una corrección "derivada" (desde otro
dispositivo o sin caché) eso pisó valores que SISOC ya tenía. La 1.1.46 lo
corrigió.

Qué señales hay en SISOC (ver el PR para el detalle):

* ``PrimerSeguimiento`` y sus bloques no tienen fecha de modificación ni
  historial (no están en django-auditlog). La única señal con hora e id de
  registro es la línea que deja la API en ``info.log``:
  ``Primer seguimiento <id> actualizado correctamente``.
* ``Relevamiento`` sí está en django-auditlog, pero solo sus campos propios: los
  bloques anidados (espacio, prestación, recursos...) no tienen historial.
* El sello ``_v`` de la app no llega a SISOC (la app lo quita antes del PATCH) y
  la app no manda ``X-App-Version``.

Por eso este módulo trabaja con *evidencias* (id + hora + fuente) que salen de
los logs, de auditlog o de ids informados a mano, y nunca repara lo que no puede
probar: el caso 2 de seguimientos se reporta, no se restaura.
"""

from __future__ import annotations

import gzip
import hashlib
import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone as dt_timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from auditlog.models import LogEntry
from django.core.exceptions import FieldDoesNotExist, ValidationError
from django.db import models, transaction
from django.utils import timezone

from relevamientos.models import (
    PrimerSeguimiento,
    Relevamiento,
    ServiciosBasicosSeguimiento,
)

logger = logging.getLogger("django")

MARCA = "reparar_datos_app_2809"
UTC = dt_timezone.utc
DESDE_DEFAULT = datetime(2026, 9, 28, 21, 17, tzinfo=UTC)
CORTE_DEFAULT = datetime(2026, 9, 28, 21, 31, tzinfo=UTC)
HASTA_DEFAULT = datetime(2026, 9, 28, 21, 58, tzinfo=UTC)

SEGUIMIENTO = "seguimiento"
RELEVAMIENTO = "relevamiento"

ACCION_INVERTIR = "invertir"
ACCION_RESTAURAR = "restaurar"
ACCION_YA_REPARADO = "ya_reparado"
ACCION_CONFLICTO = "conflicto"
ACCION_SOLO_REPORTE = "solo_reporte"
ACCIONES_APLICABLES = (ACCION_INVERTIR, ACCION_RESTAURAR)

COLUMNAS = (
    "caso",
    "modelo",
    "registro_id",
    "comedor_id",
    "comedor",
    "fecha_evidencia_utc",
    "fuente",
    "tecnico",
    "estado_validacion",
    "campo",
    "valor_actual",
    "valor_anterior",
    "valor_propuesto",
    "accion",
    "detalle",
)

# Línea de ``logger.info`` de relevamientos/views/api_views.py con el formatter
# "verbose" de settings: ``[2026-09-28 18:20:01,123] api_views INFO django: ...``.
_LOG_RE = re.compile(
    r"^\[(?P<ts>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})(?:[,.]\d+)?\]"
    r".*?\b(?P<tipo>Primer seguimiento|Relevamiento) (?P<pk>\d+)"
    r" actualizado correctamente"
)

# Campos de Relevamiento que no son respuestas del formulario: nunca se restauran.
CAMPOS_CONTROL_RELEVAMIENTO = frozenset(
    {
        "id",
        "comedor",
        "estado",
        "estado_validacion",
        "observaciones_coordinador",
        "coordinador",
        "fecha_revision_coordinador",
        "sincronizado_gestionar",
        "origen",
        "asignado_desde_sisoc",
        "client_uuid",
        "deleted_at",
        "deleted_by",
        "fecha_creacion",
        "territorial_user",
    }
)


@dataclass(frozen=True)
class Evidencia:
    """Un envío (PATCH) sobre un registro: de qué modelo, cuándo y de dónde sale."""

    modelo: str
    pk: int
    momento: datetime | None  # None: id informado a mano, sin hora
    fuente: str


@dataclass(frozen=True)
class Objetivo:
    """El cambio concreto que haría ``--aplicar`` sobre una fila."""

    modelo: type
    pk: int
    attname: str
    valor_actual: object
    valor_nuevo: object
    marca: str


@dataclass
class Fila:
    caso: int
    modelo: str
    registro_id: int
    comedor_id: int | None
    comedor: str
    fecha_evidencia_utc: str
    fuente: str
    tecnico: str
    estado_validacion: str
    campo: str
    valor_actual: object
    valor_anterior: object = ""
    valor_propuesto: object = ""
    accion: str = ACCION_SOLO_REPORTE
    detalle: str = ""
    objetivo: Objetivo | None = None

    def como_dict(self):
        return {columna: _texto(getattr(self, columna)) for columna in COLUMNAS}


@dataclass
class Parametros:
    desde: datetime = DESDE_DEFAULT
    corte: datetime = CORTE_DEFAULT
    hasta: datetime = HASTA_DEFAULT
    casos: tuple = (1, 2)
    evidencias: list = field(default_factory=list)


@dataclass
class Diagnostico:
    filas: list = field(default_factory=list)
    advertencias: list = field(default_factory=list)
    revisados: dict = field(default_factory=dict)

    @property
    def aplicables(self):
        return [fila for fila in self.filas if fila.accion in ACCIONES_APLICABLES]

    def token(self):
        """Huella del conjunto exacto de cambios: ``--confirmar`` debe coincidir."""
        partes = sorted(
            "|".join(
                (
                    str(fila.caso),
                    fila.objetivo.modelo._meta.label,
                    str(fila.objetivo.pk),
                    fila.objetivo.attname,
                    repr(fila.objetivo.valor_actual),
                    repr(fila.objetivo.valor_nuevo),
                )
            )
            for fila in self.aplicables
        )
        return hashlib.sha256("\n".join(partes).encode("utf-8")).hexdigest()[:12]


# --------------------------------------------------------------------------- #
# Evidencias
# --------------------------------------------------------------------------- #


def _archivos_log(rutas):
    for ruta in rutas:
        ruta = Path(ruta)
        if ruta.is_dir():
            yield from sorted(
                p for p in ruta.rglob("*") if p.is_file() and ".log" in p.name
            )
        elif ruta.is_file():
            yield ruta
        else:
            raise FileNotFoundError(f"No existe el log {ruta}")


def _abrir_log(path):
    if path.suffix == ".gz":
        return gzip.open(path, "rt", encoding="utf-8", errors="replace")
    return path.open(encoding="utf-8", errors="replace")


def leer_logs(rutas, tz_nombre):
    """Evidencias desde ``info.log`` (archivos o carpetas; acepta ``.gz``).

    ``asctime`` está en la hora local del proceso: Django fija ``TZ`` con
    ``settings.TIME_ZONE``, así que por defecto se interpreta en esa zona y se
    pasa a UTC.
    """
    zona = ZoneInfo(tz_nombre)
    evidencias = []
    for path in _archivos_log(rutas):
        with _abrir_log(path) as archivo:
            for numero, linea in enumerate(archivo, start=1):
                match = _LOG_RE.search(linea)
                if not match:
                    continue
                local = datetime.strptime(match["ts"], "%Y-%m-%d %H:%M:%S")
                modelo = (
                    SEGUIMIENTO
                    if match["tipo"] == "Primer seguimiento"
                    else RELEVAMIENTO
                )
                evidencias.append(
                    Evidencia(
                        modelo=modelo,
                        pk=int(match["pk"]),
                        momento=local.replace(tzinfo=zona).astimezone(UTC),
                        fuente=f"log:{path.name}:{numero}",
                    )
                )
    return evidencias


def evidencias_manuales(modelo, ids):
    return [Evidencia(modelo, int(pk), None, "manual") for pk in ids]


def _en_ventana(evidencia, desde, hasta):
    if evidencia.momento is None:
        return True
    return desde <= evidencia.momento < hasta


def _primera_por_registro(evidencias, modelo, desde, hasta):
    """La primera evidencia de cada registro dentro de ``[desde, hasta)``."""
    primeras = {}
    for evidencia in evidencias:
        if evidencia.modelo != modelo or not _en_ventana(evidencia, desde, hasta):
            continue
        actual = primeras.get(evidencia.pk)
        if actual is None or _clave_orden(evidencia) < _clave_orden(actual):
            primeras[evidencia.pk] = evidencia
    return [primeras[pk] for pk in sorted(primeras)]


def _clave_orden(evidencia):
    momento = evidencia.momento or datetime.max.replace(tzinfo=UTC)
    return (momento, evidencia.fuente)


def _entradas_auditlog_relevamientos(desde, hasta):
    """Historial de django-auditlog de Relevamiento dentro de la ventana.

    Se descartan las entradas que dejó esta misma reparación.
    """
    entradas = LogEntry.objects.get_for_model(Relevamiento).filter(
        action=LogEntry.Action.UPDATE,
        timestamp__gte=desde,
        timestamp__lt=hasta,
    )
    return [
        entrada
        for entrada in entradas.order_by("timestamp", "pk")
        if _dict(entrada.additional_data).get("reparacion") != MARCA
    ]


def _marcas_aplicadas():
    """Marcas de los cambios que esta reparación ya hizo (idempotencia)."""
    datos = LogEntry.objects.filter(additional_data__reparacion=MARCA).values_list(
        "additional_data", flat=True
    )
    return {_dict(dato).get("marca") for dato in datos} - {None}


# --------------------------------------------------------------------------- #
# Helpers de valores
# --------------------------------------------------------------------------- #


def _dict(valor):
    if isinstance(valor, dict):
        return valor
    if isinstance(valor, str):
        try:
            valor = json.loads(valor)
        except ValueError:
            return {}
        return valor if isinstance(valor, dict) else {}
    return {}


def _vacio(valor):
    return valor is None or valor == "" or valor == [] or valor == {}


def _vacio_en_log(valor):
    # auditlog guarda los valores como texto: un None de un campo común queda "None".
    return _vacio(valor) or valor == "None"


def _texto(valor):
    if valor is None:
        return "NULL"
    if isinstance(valor, datetime):
        return valor.astimezone(UTC).isoformat()
    return str(valor)


def _desde_auditlog(model_field, crudo):
    """Convierte el texto de ``LogEntry.changes`` al valor Python del campo."""
    if isinstance(model_field, models.JSONField):
        return json.loads(crudo) if isinstance(crudo, str) else crudo
    if model_field.is_relation:
        return model_field.target_field.to_python(crudo)
    valor = model_field.to_python(crudo)
    if isinstance(model_field, models.DateTimeField) and timezone.is_naive(valor):
        # auditlog guarda los DateTimeField en UTC sin zona.
        valor = timezone.make_aware(valor, UTC)
    return valor


def _tecnico(relevamiento, seguimiento=None):
    partes = []
    if seguimiento is not None:
        partes.append(seguimiento.tecnico)
    partes.append(relevamiento.territorial_nombre)
    usuario = relevamiento.territorial_user
    partes.append(usuario.username if usuario else None)
    vistos = []
    for parte in partes:
        if parte and parte not in vistos:
            vistos.append(parte)
    return " / ".join(vistos)


def _base_fila(caso, modelo, registro, evidencia):
    """Columnas comunes; ``registro`` es un seguimiento o un relevamiento."""
    relevamiento = registro.id_relevamiento if modelo == SEGUIMIENTO else registro
    comedor = relevamiento.comedor
    return {
        "caso": caso,
        "modelo": modelo,
        "registro_id": registro.pk,
        "comedor_id": comedor.pk if comedor else None,
        "comedor": comedor.nombre if comedor else "",
        "fecha_evidencia_utc": _texto(evidencia.momento) if evidencia.momento else "",
        "fuente": evidencia.fuente,
        "estado_validacion": registro.estado_validacion or "",
    }


# --------------------------------------------------------------------------- #
# Casos
# --------------------------------------------------------------------------- #


def _cargar_seguimientos(ids):
    queryset = PrimerSeguimiento.objects.select_related(
        "id_relevamiento__comedor",
        "id_relevamiento__territorial_user",
        *PrimerSeguimiento.BLOQUES_ONE_TO_ONE,
    ).filter(pk__in=ids)
    return {seguimiento.pk: seguimiento for seguimiento in queryset}


def _envios_posteriores(evidencias, corte):
    """Primer envío de cada seguimiento desde ``corte`` (sin tope de fin).

    La 1.1.45+ lee ``elementos_guardados`` de SISOC, lo muestra invertido y lo
    reenvía: tras un envío posterior el valor puede estar bien (el técnico lo
    corrigió) o seguir mal (no lo tocó). No se puede saber, así que no se invierte.
    """
    posteriores = {}
    for evidencia in evidencias:
        if evidencia.modelo != SEGUIMIENTO or evidencia.momento is None:
            continue
        if evidencia.momento < corte:
            continue
        actual = posteriores.get(evidencia.pk)
        if actual is None or evidencia.momento < actual.momento:
            posteriores[evidencia.pk] = evidencia
    return posteriores


def _filas_caso1(evidencias, seguimientos, marcas, posteriores):
    filas = []
    for evidencia in evidencias:
        seguimiento = seguimientos[evidencia.pk]
        bloque = seguimiento.servicios_basicos
        if bloque is None or bloque.elementos_guardados is None:
            continue
        actual = bloque.elementos_guardados
        marca = (
            f"{MARCA}:caso1:{bloque._meta.label_lower}:{bloque.pk}:elementos_guardados"
        )
        fila = Fila(
            **_base_fila(1, SEGUIMIENTO, seguimiento, evidencia),
            tecnico=_tecnico(seguimiento.id_relevamiento, seguimiento),
            campo="servicios_basicos.elementos_guardados",
            valor_actual=actual,
        )
        posterior = posteriores.get(seguimiento.pk)
        if marca in marcas:
            fila.accion = ACCION_YA_REPARADO
            fila.detalle = "ya invertido por esta reparación"
        elif posterior is not None:
            fila.accion = ACCION_CONFLICTO
            fila.detalle = (
                f"reenviado después ({_texto(posterior.momento)}, {posterior.fuente}): "
                "el valor puede haberse corregido; revisar a mano"
            )
        else:
            fila.accion = ACCION_INVERTIR
            fila.valor_propuesto = not actual
            fila.objetivo = Objetivo(
                ServiciosBasicosSeguimiento,
                bloque.pk,
                "elementos_guardados",
                actual,
                not actual,
                marca,
            )
        filas.append(fila)
    return filas


def _campos_vacios(instancia):
    vacios, con_valor = [], 0
    for model_field in instancia._meta.concrete_fields:
        if model_field.primary_key:
            continue
        if _vacio(model_field.value_from_object(instancia)):
            vacios.append(model_field.name)
        else:
            con_valor += 1
    return vacios, con_valor


def _filas_caso2_seguimientos(evidencias, seguimientos):
    """Sin historial: se listan los campos vacíos de cada bloque con datos.

    ``_upsert_block`` solo escribe un bloque si el payload trae algún valor, y en
    ese caso pone en ``None`` todos los ``''``: los bloques que quedaron con
    datos y campos vacíos son los que pudo vaciar la 1.1.45.
    """
    filas = []
    for evidencia in evidencias:
        seguimiento = seguimientos[evidencia.pk]
        base = _base_fila(2, SEGUIMIENTO, seguimiento, evidencia)
        tecnico = _tecnico(seguimiento.id_relevamiento, seguimiento)
        if _vacio(seguimiento.tecnico):
            filas.append(
                Fila(
                    **base,
                    tecnico=tecnico,
                    campo="tecnico",
                    valor_actual=seguimiento.tecnico,
                    valor_anterior="(sin historial)",
                    detalle="la 1.1.45 mandaba tecnico='' sin uid",
                )
            )
        for relacion in PrimerSeguimiento.BLOQUES_ONE_TO_ONE:
            bloque = getattr(seguimiento, relacion)
            if bloque is None:
                continue
            vacios, con_valor = _campos_vacios(bloque)
            if not vacios or not con_valor:
                continue
            filas.append(
                Fila(
                    **base,
                    tecnico=tecnico,
                    campo=f"{relacion}: {', '.join(vacios)}",
                    valor_actual=None,
                    valor_anterior="(sin historial)",
                    detalle=(
                        f"{len(vacios)} campos vacíos en un bloque con "
                        f"{con_valor} con valor; comparar con el papel"
                    ),
                )
            )
    return filas


def _fila_relevamiento_desde_cambio(relevamiento, entrada, campo, par, marcas):
    """Una fila por campo que auditlog vio pasar de un valor a vacío."""
    anterior_crudo, nuevo_crudo = par
    model_field = Relevamiento._meta.get_field(campo)
    evidencia = Evidencia(
        RELEVAMIENTO, relevamiento.pk, entrada.timestamp, f"auditlog:{entrada.pk}"
    )
    base = _base_fila(2, RELEVAMIENTO, relevamiento, evidencia)
    actual = model_field.value_from_object(relevamiento)
    fila = Fila(
        **base,
        tecnico=_tecnico(relevamiento),
        campo=campo,
        valor_actual=actual,
        valor_anterior=anterior_crudo,
        detalle=f"auditlog: {anterior_crudo!r} -> {nuevo_crudo!r}",
    )
    try:
        anterior = _desde_auditlog(model_field, anterior_crudo)
    except (ValidationError, ValueError, TypeError):
        fila.accion = ACCION_CONFLICTO
        fila.detalle += "; el valor anterior no se pudo interpretar"
        return fila
    marca = f"{MARCA}:caso2:{Relevamiento._meta.label_lower}:{relevamiento.pk}:{campo}"
    if marca in marcas:
        fila.accion = ACCION_YA_REPARADO
        fila.detalle += "; ya restaurado por esta reparación"
    elif _vacio(actual):
        fila.accion = ACCION_RESTAURAR
        fila.valor_propuesto = anterior
        fila.objetivo = Objetivo(
            Relevamiento, relevamiento.pk, model_field.attname, actual, anterior, marca
        )
    elif actual == anterior:
        fila.accion = ACCION_YA_REPARADO
        fila.detalle += "; ya tiene el valor anterior"
    else:
        fila.accion = ACCION_CONFLICTO
        fila.detalle += "; cambió después del vaciado, no se toca"
    return fila


def _campo_restaurable(campo):
    if campo in CAMPOS_CONTROL_RELEVAMIENTO:
        return False
    try:
        model_field = Relevamiento._meta.get_field(campo)
    except FieldDoesNotExist:
        return False
    return model_field.concrete and not model_field.many_to_many


def _filas_caso2_relevamientos(entradas, evidencias, relevamientos, marcas):
    filas = []
    vistos = set()
    con_historial = set()
    for entrada in entradas:
        relevamiento = relevamientos.get(int(entrada.object_pk))
        if relevamiento is None:
            continue
        cambios = _dict(entrada.changes) or _dict(entrada.changes_text)
        for campo, par in cambios.items():
            if not isinstance(par, (list, tuple)) or len(par) != 2:
                continue
            if not _campo_restaurable(campo) or (relevamiento.pk, campo) in vistos:
                continue
            if not _vacio_en_log(par[1]) or _vacio_en_log(par[0]):
                continue
            vistos.add((relevamiento.pk, campo))
            con_historial.add(relevamiento.pk)
            filas.append(
                _fila_relevamiento_desde_cambio(
                    relevamiento, entrada, campo, par, marcas
                )
            )
    for evidencia in evidencias:
        relevamiento = relevamientos.get(evidencia.pk)
        if relevamiento is None or relevamiento.pk in con_historial:
            continue
        filas.append(
            Fila(
                **_base_fila(2, RELEVAMIENTO, relevamiento, evidencia),
                tecnico=_tecnico(relevamiento),
                campo="(bloques anidados)",
                valor_actual="-",
                valor_anterior="(sin historial)",
                detalle=(
                    "hubo envío en la ventana; auditlog no registró campos "
                    "propios vaciados y los bloques anidados no tienen historial"
                ),
            )
        )
    return filas


def _faltantes(evidencias, encontrados, modelo, diagnostico):
    for evidencia in evidencias:
        if evidencia.pk not in encontrados:
            diagnostico.advertencias.append(
                f"{modelo} {evidencia.pk} ({evidencia.fuente}) no existe en la base."
            )
    return [evidencia for evidencia in evidencias if evidencia.pk in encontrados]


def diagnosticar(parametros):
    """Arma el diagnóstico completo. Solo lectura."""
    diagnostico = Diagnostico()
    marcas = _marcas_aplicadas()
    seg_1 = _primera_por_registro(
        parametros.evidencias, SEGUIMIENTO, parametros.desde, parametros.corte
    )
    seg_2 = _primera_por_registro(
        parametros.evidencias, SEGUIMIENTO, parametros.corte, parametros.hasta
    )
    rel_2 = _primera_por_registro(
        parametros.evidencias, RELEVAMIENTO, parametros.corte, parametros.hasta
    )
    seguimientos = _cargar_seguimientos({e.pk for e in seg_1 + seg_2})
    seg_1 = _faltantes(seg_1, seguimientos, "Seguimiento", diagnostico)
    seg_2 = _faltantes(seg_2, seguimientos, "Seguimiento", diagnostico)

    if 1 in parametros.casos:
        posteriores = _envios_posteriores(parametros.evidencias, parametros.corte)
        diagnostico.filas += _filas_caso1(seg_1, seguimientos, marcas, posteriores)
        diagnostico.revisados["caso 1 · seguimientos"] = len(seg_1)
    if 2 in parametros.casos:
        entradas = _entradas_auditlog_relevamientos(parametros.corte, parametros.hasta)
        ids = {int(e.object_pk) for e in entradas} | {e.pk for e in rel_2}
        relevamientos = {
            relevamiento.pk: relevamiento
            for relevamiento in Relevamiento.all_objects.select_related(
                "comedor", "territorial_user"
            ).filter(pk__in=ids)
        }
        rel_2 = _faltantes(rel_2, relevamientos, "Relevamiento", diagnostico)
        diagnostico.filas += _filas_caso2_seguimientos(seg_2, seguimientos)
        diagnostico.filas += _filas_caso2_relevamientos(
            entradas, rel_2, relevamientos, marcas
        )
        diagnostico.revisados["caso 2 · seguimientos"] = len(seg_2)
        diagnostico.revisados["caso 2 · relevamientos"] = len(relevamientos)
        diagnostico.revisados["caso 2 · entradas de auditlog"] = len(entradas)
    return diagnostico


# --------------------------------------------------------------------------- #
# Reparación
# --------------------------------------------------------------------------- #


class CambioConcurrenteError(Exception):
    """El registro cambió entre el diagnóstico y la escritura."""


def _manager(modelo):
    # `all_objects` incluye los soft-deleted (Relevamiento); el resto usa `objects`.
    return getattr(modelo, "all_objects", modelo.objects)


def _aplicar_fila(fila):
    objetivo = fila.objetivo
    actualizados = (
        _manager(objetivo.modelo)
        .filter(pk=objetivo.pk, **{objetivo.attname: objetivo.valor_actual})
        .update(**{objetivo.attname: objetivo.valor_nuevo})
    )
    if actualizados != 1:
        raise CambioConcurrenteError(
            f"{objetivo.modelo._meta.label}#{objetivo.pk}.{objetivo.attname} cambió "
            "durante la reparación; no se aplicó nada."
        )
    instancia = _manager(objetivo.modelo).get(pk=objetivo.pk)
    LogEntry.objects.log_create(
        instancia,
        force_log=True,
        action=LogEntry.Action.UPDATE,
        changes={
            objetivo.attname: [
                _texto(objetivo.valor_actual),
                _texto(objetivo.valor_nuevo),
            ]
        },
        additional_data={
            "reparacion": MARCA,
            "marca": objetivo.marca,
            "caso": fila.caso,
            "registro": f"{fila.modelo}#{fila.registro_id}",
            "evidencia": fila.fuente,
            "audittrail_source": MARCA,
            "audittrail_batch_key": objetivo.marca,
        },
    )
    mensaje = (
        f"[{MARCA}] caso {fila.caso} {fila.modelo}#{fila.registro_id} "
        f"{objetivo.modelo._meta.label}#{objetivo.pk}.{objetivo.attname}: "
        f"{_texto(objetivo.valor_actual)} -> {_texto(objetivo.valor_nuevo)}"
    )
    logger.info(mensaje)
    return mensaje


def aplicar(parametros, confirmacion):
    """Recalcula el diagnóstico y aplica sus cambios en una sola transacción.

    Devuelve ``(diagnostico, mensajes)``. Si ``confirmacion`` no coincide con el
    token del conjunto actual de cambios no escribe nada. Correrlo de nuevo no
    repite cambios: cada uno deja una marca en auditlog.
    """
    with transaction.atomic():
        diagnostico = diagnosticar(parametros)
        aplicables = diagnostico.aplicables
        if not aplicables:
            return diagnostico, []
        if confirmacion != diagnostico.token():
            raise ValueError(
                "La confirmación no coincide con el conjunto actual de cambios "
                f"(token {diagnostico.token()}). Volvé a correr sin --aplicar y "
                "revisá la lista."
            )
        mensajes = [_aplicar_fila(fila) for fila in aplicables]
    return diagnostico, mensajes
