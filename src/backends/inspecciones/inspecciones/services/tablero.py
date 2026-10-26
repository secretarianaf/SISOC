"""Tablero en vivo de coordinación (especificación funcional §9 y §15).

Reglas que sigue todo el módulo:

- Sólo cuentan las actas **válidas**: ``estado = finalizada`` y
  ``es_prueba = False``. Las anuladas y las de prueba nunca entran.
- Los borradores (``Inspeccion`` sin acta) se informan aparte, como avance
  provisional: no se suman a ningún resultado.
- Los mismos filtros (``Filtros``) arman un único queryset de actas que
  alimenta indicadores, mapa, tabla y CSV, así que siempre coinciden.
- Lo que se puede contar en la base se cuenta en la base. De la
  ``instantanea`` se leen sólo las partes necesarias (ubicación, respuestas,
  firma y escuela, no el formulario ni las imágenes) y sólo del conjunto
  filtrado: la cantidad de consultas no depende del volumen.
- Ausentismo observado y aulas en funcionamiento: sumas de numeradores sobre
  sumas de denominadores, sólo con actas constatadas (total o parcial) con los
  dos valores conocidos y el denominador mayor que cero. Cero es un dato.
- El mapa usa sólo coordenadas GPS: una ubicación manual no se ubica (no se
  infieren coordenadas de la dirección) y se cuenta aparte.

La respuesta se cachea ``CACHE_SEGUNDOS`` por combinación de filtros. El
cache del proyecto es en memoria por proceso (``LocMemCache``), así que cada
worker de gunicorn recalcula a lo sumo una vez cada 2 segundos.
"""

import csv
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db.models import Count, OuterRef, Q, Subquery
from django.db.models.fields.json import KeyTransform
from django.urls import NoReverseMatch, reverse
from django.utils import timezone

from core.models import Localidad, Provincia
from inspecciones.models import Acta, Inspeccion, NotificacionPapel
from inspecciones.services.formato import fecha_desde_texto, hoy, iso
from inspecciones.services.formularios import VERSION_ACTUAL, obtener_formulario
from users.services_inspecciones import ROL_INSPECTOR

CACHE_SEGUNDOS = 2
CACHE_PREFIJO = "inspecciones:tablero:v1"
MAX_ULTIMAS = 20

NOTIFICACIONES = (
    (Acta.EstadoNotificacion.PENDIENTE.value, "Pendiente"),
    (Acta.EstadoNotificacion.CARGADA.value, "Cargada"),
)

SIN_DATO = "sin_dato"
CONSTATADAS = ("constatado", "parcial")

# Etiquetas cortas para el tablero (las completas, en el CSV, salen del
# formulario guardado).
RESULTADOS = (
    ("constatado", "Se pudo constatar"),
    ("parcial", "Constatación parcial"),
    ("cerrada", "Escuela cerrada"),
    ("no_ingreso", "No dejó ingresar"),
    (SIN_DATO, "Sin dato"),
)
PRESENCIA = (
    ("si", "Sí"),
    ("no", "No"),
    ("no_constatado", "No constatado"),
    (SIN_DATO, "Sin dato"),
)
MOTIVOS_SIN_FIRMA = (
    ("negativa", "negativa"),
    ("ausente", "ausente"),
    ("otra", "otra imposibilidad"),
    (SIN_DATO, "sin dato"),
)

_PAYLOAD = KeyTransform("payload", "instantanea")
_MARCA_NUMERO = "__NUMERO__"


# --- Filtros ------------------------------------------------------------------


def _turnos():
    return [
        (t["valor"], t["etiqueta"])
        for t in obtener_formulario(VERSION_ACTUAL)["turnos"]
    ]


def _entero(valor):
    valor = str(valor or "").strip()
    return int(valor) if valor.isdigit() else None


@dataclass(frozen=True)
class Filtros:
    """Filtros del tablero, ya validados (un valor inválido se ignora)."""

    fecha: date
    provincia: int | None = None
    localidad: int | None = None
    inspector: int | None = None
    turno: str = ""
    notificacion: str = ""

    def clave(self):
        partes = (
            self.fecha.isoformat(),
            self.provincia or "",
            self.localidad or "",
            self.inspector or "",
            self.turno,
            self.notificacion,
        )
        return ":".join(str(parte) for parte in partes)

    def como_querystring(self):
        return {
            "fecha": self.fecha.isoformat(),
            "provincia": self.provincia or "",
            "localidad": self.localidad or "",
            "inspector": self.inspector or "",
            "turno": self.turno,
            "notificacion": self.notificacion,
        }


def leer_filtros(params):
    """``Filtros`` desde el querystring. La fecha por defecto es hoy (AR)."""
    turno = str(params.get("turno") or "").strip()
    notificacion = str(params.get("notificacion") or "").strip()
    return Filtros(
        fecha=fecha_desde_texto(params.get("fecha")) or hoy(),
        provincia=_entero(params.get("provincia")),
        localidad=_entero(params.get("localidad")),
        inspector=_entero(params.get("inspector")),
        turno=turno if turno in dict(_turnos()) else "",
        notificacion=notificacion if notificacion in dict(NOTIFICACIONES) else "",
    )


def actas_validas(filtros):
    """Actas que cuentan, con los filtros aplicados. Fuente única del tablero."""
    queryset = Acta.objects.filter(
        estado=Acta.Estado.FINALIZADA,
        es_prueba=False,
        fecha_visita=filtros.fecha,
    )
    if filtros.provincia:
        queryset = queryset.filter(escuela__provincia_id=filtros.provincia)
    if filtros.localidad:
        queryset = queryset.filter(escuela__localidad_vinculada_id=filtros.localidad)
    if filtros.inspector:
        queryset = queryset.filter(inspector_id=filtros.inspector)
    if filtros.turno:
        queryset = queryset.filter(turno=filtros.turno)
    if filtros.notificacion:
        queryset = queryset.filter(notificacion_estado=filtros.notificacion)
    return queryset


def _rango_del_dia(fecha):
    # Rango explícito en vez de ``__date``: en MySQL ``__date`` con USE_TZ
    # depende de que estén cargadas las tablas de zonas horarias.
    inicio = timezone.make_aware(datetime.combine(fecha, time.min))
    return inicio, inicio + timedelta(days=1)


def borradores_en_curso(filtros):
    """Borradores con datos de la jornada (sin fecha: los guardados ese día).

    El filtro de notificación no aplica: un borrador todavía no la tiene.
    """
    inicio, fin = _rango_del_dia(filtros.fecha)
    queryset = Inspeccion.objects.filter(
        estado=Inspeccion.Estado.BORRADOR, revision__gt=0
    ).filter(
        Q(fecha_visita=filtros.fecha)
        | Q(fecha_visita__isnull=True, guardada_at__gte=inicio, guardada_at__lt=fin)
    )
    if filtros.provincia:
        queryset = queryset.filter(escuela__provincia_id=filtros.provincia)
    if filtros.localidad:
        queryset = queryset.filter(escuela__localidad_vinculada_id=filtros.localidad)
    if filtros.inspector:
        queryset = queryset.filter(inspector_id=filtros.inspector)
    if filtros.turno:
        queryset = queryset.filter(turno=filtros.turno)
    return queryset


def inspectores_habilitados():
    """Usuarios activos con rol inspector en el programa."""
    return get_user_model().objects.filter(
        is_active=True,
        profile__es_inspector_escolar=True,
        profile__inspecciones_rol=ROL_INSPECTOR,
    )


# --- Opciones de la página ------------------------------------------------------


def _nombre(first_name, last_name, username):
    return f"{first_name or ''} {last_name or ''}".strip() or username or ""


def opciones_filtros():
    """Provincias, inspectores, turnos y estados de notificación."""
    inspectores = sorted(
        (
            {"id": pk, "nombre": _nombre(nombre, apellido, usuario)}
            for pk, nombre, apellido, usuario in inspectores_habilitados().values_list(
                "id", "first_name", "last_name", "username"
            )
        ),
        key=lambda i: i["nombre"].lower(),
    )
    return {
        "provincias": list(Provincia.objects.order_by("nombre").values("id", "nombre")),
        "inspectores": inspectores,
        "turnos": [{"valor": v, "etiqueta": e} for v, e in _turnos()],
        "notificaciones": [{"valor": v, "etiqueta": e} for v, e in NOTIFICACIONES],
    }


def _localidades_con_actas(filtros):
    """Localidades de la provincia elegida que tienen actas válidas en la fecha."""
    if not filtros.provincia:
        return []
    ids = (
        Acta.objects.filter(
            estado=Acta.Estado.FINALIZADA,
            es_prueba=False,
            fecha_visita=filtros.fecha,
            escuela__provincia_id=filtros.provincia,
            escuela__localidad_vinculada__isnull=False,
        )
        .values("escuela__localidad_vinculada_id")
        .order_by()
    )
    filas = (
        Localidad.objects.filter(id__in=ids)
        .order_by("nombre", "municipio__nombre")
        .values_list("id", "nombre", "municipio__nombre")
    )
    return [
        {"id": pk, "nombre": f"{nombre} · {municipio}" if municipio else nombre}
        for pk, nombre, municipio in filas
    ]


# --- Lectura de la instantánea --------------------------------------------------


def _dict(valor):
    return valor if isinstance(valor, dict) else {}


def _cantidad(respuesta):
    """Entero ≥ 0 si la respuesta es un dato conocido; ``None`` si no."""
    respuesta = _dict(respuesta)
    if respuesta.get("condicion", "dato") != "dato":
        return None
    valor = respuesta.get("valor")
    if isinstance(valor, bool) or not isinstance(valor, (int, float)):
        return None
    if valor < 0 or int(valor) != valor:
        return None
    return int(valor)


def _coordenada(valor, limite):
    if isinstance(valor, bool) or not isinstance(valor, (int, float)):
        return None
    return float(valor) if -limite <= valor <= limite else None


def _escuela_de(fila):
    """Nombre y Cueanexo tal como quedaron en el acta (con el catálogo de respaldo)."""
    escuela = _dict(fila.get("escuela_acta"))
    nombre = escuela.get("nombre") or fila.get("escuela__nombre") or ""
    cue = escuela.get("cue") or fila.get("escuela__cue") or fila.get("escuela__codigo")
    return str(nombre), str(cue or "")


def _clave_escuela(fila):
    """Clave del establecimiento para deduplicar (§5)."""
    if fila["escuela_id"]:
        return ("catalogo", fila["escuela_id"])
    _, cue = _escuela_de(fila)
    cue = "".join(cue.split())
    if cue:
        return ("cue", cue)
    return ("acta", fila["id"])


def _valores_para_tablero():
    return {
        "ubicacion": KeyTransform("ubicacion", _PAYLOAD),
        "respuestas": KeyTransform("respuestas", _PAYLOAD),
        "firma": KeyTransform("firma", _PAYLOAD),
        "escuela_acta": KeyTransform("escuela", _PAYLOAD),
    }


CAMPOS_FILA = (
    "id",
    "numero",
    "cerrada_at",
    "fecha_visita",
    "turno",
    "resultado",
    "firma_tipo",
    "notificacion_estado",
    "escuela_id",
    "inspector_id",
    "inspector__first_name",
    "inspector__last_name",
    "inspector__username",
    "escuela__nombre",
    "escuela__cue",
    "escuela__codigo",
    "escuela__provincia__nombre",
)


# --- Cálculos -------------------------------------------------------------------


def _indice(filas, previsto, presente):
    """Agregado de un índice con su regla de computabilidad (§9)."""
    excluidas = Counter()
    suma_previsto = suma_presente = computables = 0
    colegios = set()
    for fila in filas:
        if fila["resultado"] not in CONSTATADAS:
            excluidas["sin_constatacion"] += 1
            continue
        respuestas = _dict(fila["respuestas"])
        valor_previsto = _cantidad(respuestas.get(previsto))
        valor_presente = _cantidad(respuestas.get(presente))
        if valor_previsto is None or valor_presente is None:
            excluidas[SIN_DATO] += 1
            continue
        if valor_previsto == 0:
            excluidas["denominador_cero"] += 1
            continue
        computables += 1
        colegios.add(_clave_escuela(fila))
        suma_previsto += valor_previsto
        suma_presente += valor_presente
    return {
        "previsto": suma_previsto,
        "presente": suma_presente,
        "computables": computables,
        "colegios": len(colegios),
        "excluidas": len(filas) - computables,
        "motivos_exclusion": {
            "sin_constatacion": excluidas["sin_constatacion"],
            SIN_DATO: excluidas[SIN_DATO],
            "denominador_cero": excluidas["denominador_cero"],
        },
    }


def _ausentismo(filas):
    indice = _indice(filas, "f09", "f10")
    previsto, presente = indice["previsto"], indice["presente"]
    indice["porcentaje"] = (
        round((previsto - presente) * 100 / previsto, 1) if previsto else None
    )
    return indice


def _aulas(filas):
    indice = _indice(filas, "f11", "f12")
    previstas, funcionando = indice["previsto"], indice["presente"]
    indice["porcentaje"] = (
        round(funcionando * 100 / previstas, 1) if previstas else None
    )
    return indice


def _presencia(filas, codigo):
    conteo = Counter()
    for fila in filas:
        valor = _dict(fila["respuestas"]).get(codigo)
        conteo[valor if valor in ("si", "no", "no_constatado") else SIN_DATO] += 1
    return {
        "categorias": [
            {"valor": v, "etiqueta": e, "cantidad": conteo[v]} for v, e in PRESENCIA
        ],
        "denominador": conteo["si"] + conteo["no"] + conteo["no_constatado"],
        "total": len(filas),
    }


def _distribucion(queryset, campo, opciones):
    """Conteo agrupado en la base, con las categorías en orden fijo."""
    conteo = Counter()
    for valor, cantidad in (
        queryset.values_list(campo).annotate(n=Count("id")).order_by()
    ):
        conteo[valor if valor in dict(opciones) else SIN_DATO] += cantidad
    categorias = [
        {"valor": v, "etiqueta": e, "cantidad": conteo[v]} for v, e in opciones
    ]
    return [c for c in categorias if c["valor"] != SIN_DATO or c["cantidad"]]


def _url_detalle_base():
    try:
        return reverse("inspecciones_acta_detalle", args=[_MARCA_NUMERO])
    except NoReverseMatch:
        return None


def _url_detalle(base, numero):
    return base.replace(_MARCA_NUMERO, numero) if base else None


def _ubicacion_gps(fila):
    ubicacion = _dict(fila["ubicacion"])
    if ubicacion.get("fuente") != "gps":
        return None
    lat = _coordenada(ubicacion.get("lat"), 90)
    lng = _coordenada(ubicacion.get("lng"), 180)
    if lat is None or lng is None:
        return None
    return lat, lng


def _firma(fila):
    if fila["firma_tipo"] == "firma":
        return {"tipo": "firma", "etiqueta": "Firmada", "motivo": None}
    motivo = _dict(fila["firma"]).get("motivo_tipo")
    motivo = motivo if motivo in dict(MOTIVOS_SIN_FIRMA) else SIN_DATO
    return {
        "tipo": "excepcion",
        "etiqueta": f"Sin firma: {dict(MOTIVOS_SIN_FIRMA)[motivo]}",
        "motivo": motivo,
    }


def _resumen_fila(fila, *, url_base, turnos, resultados):
    nombre, cue = _escuela_de(fila)
    return {
        "numero": fila["numero"],
        "url": _url_detalle(url_base, fila["numero"]),
        "escuela": nombre,
        "cueanexo": cue,
        "turno": turnos.get(fila["turno"], fila["turno"] or "Sin dato"),
        "inspector": _nombre(
            fila["inspector__first_name"],
            fila["inspector__last_name"],
            fila["inspector__username"],
        ),
        "resultado": resultados.get(fila["resultado"], "Sin dato"),
    }


def _mapa(filas, contexto):
    puntos = []
    conteo = Counter()
    for fila in filas:
        coordenadas = _ubicacion_gps(fila)
        if coordenadas is None:
            fuente = _dict(fila["ubicacion"]).get("fuente")
            conteo["manual" if fuente == "manual" else SIN_DATO] += 1
            continue
        puntos.append(
            {
                **_resumen_fila(fila, **contexto),
                "lat": coordenadas[0],
                "lng": coordenadas[1],
                "constatada": fila["resultado"] in CONSTATADAS,
            }
        )
    return {
        "puntos": puntos,
        "con_gps": len(puntos),
        "sin_coordenadas": conteo["manual"] + conteo[SIN_DATO],
        "manual": conteo["manual"],
        "sin_ubicacion": conteo[SIN_DATO],
    }


def _ultimas(filas, contexto):
    notificaciones = dict(NOTIFICACIONES)
    return [
        {
            **_resumen_fila(fila, **contexto),
            "cerrada_at": iso(fila["cerrada_at"]),
            "hora": timezone.localtime(fila["cerrada_at"]).strftime("%H:%M"),
            "provincia": fila["escuela__provincia__nombre"] or "",
            "firma": _firma(fila),
            "notificacion": {
                "estado": fila["notificacion_estado"],
                "etiqueta": notificaciones.get(
                    fila["notificacion_estado"], fila["notificacion_estado"]
                ),
            },
        }
        for fila in filas[:MAX_ULTIMAS]
    ]


def _inspectores(filas, filtros):
    habilitados = set(inspectores_habilitados().values_list("id", flat=True))
    activos = {fila["inspector_id"] for fila in filas}
    activos.update(
        borradores_en_curso(filtros)
        .values_list("inspector_id", flat=True)
        .distinct()
        .order_by()
    )
    con_actividad = len(activos & habilitados)
    return {
        "con_actividad": con_actividad,
        "habilitados": len(habilitados),
        "sin_actividad": len(habilitados) - con_actividad,
    }


def calcular_tablero(filtros):
    """Todo el tablero en un diccionario listo para JSON (sin cache)."""
    queryset = actas_validas(filtros)
    totales = queryset.aggregate(
        actas=Count("id"),
        con_firma=Count("id", filter=Q(firma_tipo="firma")),
        notificacion_pendiente=Count(
            "id", filter=Q(notificacion_estado=Acta.EstadoNotificacion.PENDIENTE)
        ),
        notificacion_cargada=Count(
            "id", filter=Q(notificacion_estado=Acta.EstadoNotificacion.CARGADA)
        ),
    )
    filas = list(
        queryset.order_by("-cerrada_at", "-id").values(
            *CAMPOS_FILA, **_valores_para_tablero()
        )
    )
    visitas = Counter(_clave_escuela(fila) for fila in filas)
    motivos = Counter(
        _firma(fila)["motivo"] for fila in filas if fila["firma_tipo"] != "firma"
    )
    contexto = {
        "url_base": _url_detalle_base(),
        "turnos": dict(_turnos()),
        "resultados": dict(RESULTADOS),
    }
    return {
        "generado_at": iso(timezone.now()),
        "filtros": filtros.como_querystring(),
        "indicadores": {
            "escuelas_unicas": len(visitas),
            "actas_validas": totales["actas"],
            "escuelas_con_mas_de_una_visita": sum(1 for n in visitas.values() if n > 1),
            "inspectores": _inspectores(filas, filtros),
            "con_firma": totales["con_firma"],
            "sin_firma": totales["actas"] - totales["con_firma"],
            "sin_firma_por_motivo": [
                {"valor": v, "etiqueta": e, "cantidad": motivos[v]}
                for v, e in MOTIVOS_SIN_FIRMA
                if motivos[v] or v != SIN_DATO
            ],
            "borradores_en_curso": borradores_en_curso(filtros).count(),
            "notificacion_pendiente": totales["notificacion_pendiente"],
            "notificacion_cargada": totales["notificacion_cargada"],
        },
        "turnos": _distribucion(
            queryset, "turno", [*_turnos(), (SIN_DATO, "Sin dato")]
        ),
        "resultados": _distribucion(queryset, "resultado", RESULTADOS),
        "ausentismo": _ausentismo(filas),
        "aulas": _aulas(filas),
        "presencia": {
            "personal": _presencia(filas, "f07"),
            "estudiantes": _presencia(filas, "f08"),
        },
        "mapa": _mapa(filas, contexto),
        "ultimas": _ultimas(filas, contexto),
        "opciones": {"localidades": _localidades_con_actas(filtros)},
    }


def datos_tablero(filtros):
    """``calcular_tablero`` con cache corto por combinación de filtros."""
    clave = f"{CACHE_PREFIJO}:{filtros.clave()}"
    datos = cache.get(clave)
    if datos is None:
        datos = calcular_tablero(filtros)
        cache.set(clave, datos, CACHE_SEGUNDOS)
    return datos


# --- Exportación CSV ------------------------------------------------------------

_INICIO_FORMULA = ("=", "+", "-", "@", "\t", "\r")


def _celda(valor):
    """Texto plano para la planilla; neutraliza fórmulas (CSV injection)."""
    if valor is None:
        return ""
    if isinstance(valor, bool):
        return "Sí" if valor else "No"
    texto = str(valor)
    return "'" + texto if texto.startswith(_INICIO_FORMULA) else texto


def _etiquetas(formulario, grupo):
    return {o["valor"]: o["etiqueta"] for o in formulario["opciones"][grupo]}


def columnas_csv():
    """Encabezados estables: no cambian con los datos ni con los filtros."""
    preguntas = obtener_formulario(VERSION_ACTUAL)["preguntas"]

    def pregunta(codigo, sufijo=""):
        return f"{codigo.upper()} {preguntas[codigo]}{sufijo}"

    return [
        "Número de acta",
        "Fecha de visita",
        "Cierre (hora oficial)",
        "Escuela",
        "Cueanexo",
        "Provincia",
        "Localidad",
        "Distrito",
        "Turno",
        "Inspector",
        "Resultado de la constatación",
        "Motivo de la constatación parcial",
        "Qué ocurrió (no dejó ingresar)",
        pregunta("f05"),
        pregunta("f06", " - nombre"),
        pregunta("f06", " - función/rol"),
        pregunta("f07"),
        pregunta("f08"),
        pregunta("f09"),
        pregunta("f09", " - condición"),
        pregunta("f10"),
        pregunta("f10", " - condición"),
        pregunta("f11"),
        pregunta("f11", " - condición"),
        pregunta("f12"),
        pregunta("f12", " - condición"),
        pregunta("f13"),
        pregunta("f14"),
        pregunta("f15", " (cantidad)"),
        pregunta("f16"),
        "Firma",
        "Motivo de la excepción de firma",
        "Notificación",
        "Condición de firma de la notificación",
    ]


def _cantidad_csv(respuesta, condiciones):
    """(valor, condición) de F09–F12: el valor sólo si es un dato conocido."""
    respuesta = _dict(respuesta)
    if not respuesta:
        return "", "Sin dato"
    valor = _cantidad(respuesta)
    condicion = respuesta.get("condicion") or "dato"
    etiqueta = condiciones.get(condicion, condicion)
    if valor is None and condicion == "dato":
        etiqueta = "Sin dato"
    return ("" if valor is None else valor), etiqueta


def _fila_csv(fila, etiquetas):
    respuestas = _dict(fila["respuestas"])
    firma = _dict(fila["firma"])
    escuela = _dict(fila["escuela_acta"])
    nombre, cue = _escuela_de(fila)
    atiende = _dict(respuestas.get("f06"))
    f15 = fila.get("f15")
    if not isinstance(f15, list):
        f15 = respuestas.get("f15") if isinstance(respuestas.get("f15"), list) else []
    cantidades = []
    for codigo, grupo in (
        ("f09", "condicion_f09_f11"),
        ("f10", "condicion_f10_f12"),
        ("f11", "condicion_f09_f11"),
        ("f12", "condicion_f10_f12"),
    ):
        cantidades.extend(_cantidad_csv(respuestas.get(codigo), etiquetas[grupo]))
    resultado = fila["resultado"]
    es_firma = fila["firma_tipo"] == "firma"
    return [
        fila["numero"],
        fila["fecha_visita"].isoformat() if fila["fecha_visita"] else "",
        iso(fila["cerrada_at"]),
        nombre,
        cue,
        fila["escuela__provincia__nombre"],
        fila["escuela__localidad_vinculada__nombre"] or escuela.get("localidad"),
        escuela.get("distrito") or fila["escuela__distrito"],
        etiquetas["turnos"].get(fila["turno"], fila["turno"]),
        _nombre(
            fila["inspector__first_name"],
            fila["inspector__last_name"],
            fila["inspector__username"],
        ),
        etiquetas["resultado"].get(resultado, resultado),
        respuestas.get("motivo_parcial"),
        respuestas.get("que_ocurrio"),
        etiquetas["si_no"].get(respuestas.get("f05"), "Sin dato"),
        "Nadie atiende" if atiende.get("nadie") else atiende.get("nombre"),
        "" if atiende.get("nadie") else atiende.get("funcion"),
        etiquetas["constatacion"].get(respuestas.get("f07"), "Sin dato"),
        etiquetas["constatacion"].get(respuestas.get("f08"), "Sin dato"),
        *cantidades,
        resultado == "cerrada",
        resultado == "no_ingreso",
        len(f15),
        respuestas.get("f16"),
        "Firmada" if es_firma else "Excepción",
        (
            ""
            if es_firma
            else etiquetas["excepcion_firma"].get(firma.get("motivo_tipo"), "Sin dato")
        ),
        dict(NOTIFICACIONES).get(fila["notificacion_estado"]),
        etiquetas["condicion_firma"].get(fila["condicion_notificacion"], ""),
    ]


def filas_csv(filtros):
    """Una fila por acta válida (sin imagen de firma ni links a archivos)."""
    formulario = obtener_formulario(VERSION_ACTUAL)
    etiquetas = {
        grupo: _etiquetas(formulario, grupo)
        for grupo in (
            "si_no",
            "constatacion",
            "resultado",
            "condicion_f09_f11",
            "condicion_f10_f12",
            "excepcion_firma",
        )
    }
    etiquetas["turnos"] = dict(_turnos())
    etiquetas["condicion_firma"] = dict(NotificacionPapel.CondicionFirma.choices)
    ultima_condicion = (
        NotificacionPapel.objects.filter(acta=OuterRef("pk"))
        .order_by("-version")
        .values("condicion_firma")[:1]
    )
    queryset = (
        actas_validas(filtros)
        .order_by("cerrada_at", "id")
        .values(
            *CAMPOS_FILA,
            "escuela__localidad_vinculada__nombre",
            "escuela__distrito",
            condicion_notificacion=Subquery(ultima_condicion),
            f15=KeyTransform("f15", _PAYLOAD),
            **_valores_para_tablero(),
        )
    )
    yield columnas_csv()
    for fila in queryset.iterator(chunk_size=500):
        yield [_celda(valor) for valor in _fila_csv(fila, etiquetas)]


def escribir_csv(destino, filtros):
    """CSV con ``;`` (lo abre bien Excel en español).

    El BOM UTF-8 lo antepone la respuesta HTTP (``core.services.csv_export``).
    """
    escritor = csv.writer(destino, delimiter=";")
    for fila in filas_csv(filtros):
        escritor.writerow(fila)


def nombre_archivo_csv(filtros):
    return f"inspecciones-actas-{filtros.fecha.isoformat()}.csv"
