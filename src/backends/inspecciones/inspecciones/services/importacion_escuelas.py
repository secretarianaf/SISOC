"""Importación masiva del padrón de escuelas (``.xlsx`` o ``.csv``).

Columnas del padrón oficial: ``Jurisdicción, Localidad, Cueanexo, Nombre,
Domicilio, C. P., Teléfono, Mail``. ``analizar_escuelas`` (revisión) lee el
archivo, normaliza las filas y las clasifica sin escribir;
``aplicar_escuelas`` (confirmación) vuelve a clasificar esas mismas filas
normalizadas contra la base actual y guarda. Las dos usan ``_clasificar``,
así lo que se muestra en la revisión es lo que se guarda.

- Se rechazan sólo las filas sin Cueanexo válido (9 dígitos), sin Nombre o con
  una jurisdicción desconocida.
- La localidad se busca dentro de la provincia (``services.geografia``). Si
  no se resuelve, o el mail es inválido, la escuela se importa igual y queda
  "a revisar" con sus motivos.
- Una escuela que ya existe (por Cueanexo, en ``codigo`` o en ``cue``) se
  actualiza; nunca se borra nada y el ``codigo`` no cambia.
- Rendimiento (padrón real: 64.495 filas): el catálogo existente y la
  geografía se cargan una sola vez en memoria, la confirmación no relee el
  ``.xlsx`` y las escrituras son un ``INSERT`` múltiple con actualización por
  ``codigo``, en lotes de 1.000 (ver ``_guardar``).
"""

import re
from collections import Counter
from dataclasses import dataclass, field

from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import connection, transaction
from django.db.models.constants import OnConflict
from django.utils import timezone

from inspecciones.models import Escuela
from inspecciones.services.geografia import MapaGeografico, textos_de_ubicacion
from inspecciones.services.planillas import NumeroCelda, leer_planilla

LOTE = 1000
CUEANEXO_VALIDO = re.compile(r"^\d{9}$")
SEPARADORES_MAIL = re.compile(r"\s*[;,/]\s*|\s+")
MAIL_SIMPLE = re.compile(
    r"^[A-Za-z0-9_%+-]+(?:\.[A-Za-z0-9_%+-]+)*"
    r"@(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)+[A-Za-z]{2,63}$"
)
MAX_OBSERVACIONES_PANTALLA = 50
RECHAZADA = "Rechazada"

ALIAS = {
    "jurisdiccion": "jurisdiccion",
    "provincia": "jurisdiccion",
    "localidad": "localidad",
    "cueanexo": "cueanexo",
    "cue_anexo": "cueanexo",
    "cue": "cueanexo",
    "nombre": "nombre",
    "escuela": "nombre",
    "establecimiento": "nombre",
    "domicilio": "domicilio",
    "direccion": "domicilio",
    "c_p": "cp",
    "cp": "cp",
    "codigo_postal": "cp",
    "telefono": "telefono",
    "mail": "mail",
    "email": "mail",
    "correo": "mail",
}
REQUERIDAS = ("jurisdiccion", "localidad", "cueanexo", "nombre")
ETIQUETAS_COLUMNA = {
    "jurisdiccion": "Provincia",
    "localidad": "Localidad",
    "cueanexo": "Cueanexo",
    "nombre": "Nombre",
    "domicilio": "Domicilio",
    "cp": "C. P.",
    "telefono": "Teléfono",
    "mail": "Mail",
}
CAMPOS_ACTUALIZABLES = (
    "nombre",
    "cue",
    "provincia_id",
    "localidad_vinculada_id",
    "localidad",
    "distrito",
    "domicilio",
    "cp",
    "telefono",
    "mail",
    "jurisdiccion_original",
    "localidad_original",
    "a_revisar",
    "motivos_revision",
)
ETIQUETA_MOTIVO = dict(Escuela.MotivoRevision.choices)


def _texto(valor, largo):
    return " ".join(str(valor or "").split())[:largo]


def normalizar_cueanexo(valor):
    """Cueanexo de 9 dígitos o ``""``. Una celda numérica recupera sus ceros."""
    texto = "".join(str(valor or "").split())
    if isinstance(valor, NumeroCelda) and texto.isdigit() and len(texto) < 9:
        texto = texto.zfill(9)
    return texto if CUEANEXO_VALIDO.match(texto) else ""


def _mail_valido(parte):
    # Atajo: lo que pasa este patrón también lo acepta ``validate_email``
    # (que es más lento); lo demás se decide con el validador de Django.
    if len(parte) <= 254 and MAIL_SIMPLE.match(parte):
        return True
    try:
        validate_email(parte)
    except ValidationError:
        return False
    return True


def mail_valido(texto):
    """Uno o varios mails (separados por ``/``, ``;``, ``,`` o espacios)."""
    return all(_mail_valido(p) for p in SEPARADORES_MAIL.split(texto or "") if p)


@dataclass
class Clasificacion:
    """Resultado de una pasada sobre el archivo (sin escribir)."""

    total: int = 0
    nuevas: list = field(default_factory=list)
    actualizadas: list = field(default_factory=list)
    rechazadas: int = 0
    # (categoría, a_revisar) -> filas; categoría: nueva, actualizada, sin_cambios.
    categorias: Counter = field(default_factory=Counter)
    motivos: Counter = field(default_factory=Counter)
    equivalencias: dict = field(default_factory=dict)
    observaciones: list = field(default_factory=list)

    def observar(self, numero, datos, motivo, detalle):
        """Rechazo (``motivo == RECHAZADA``) o motivo por el que queda a revisar."""
        self.observaciones.append(
            {
                "fila": numero,
                "cueanexo": datos.get("cueanexo") or datos.get("cueanexo_original", ""),
                "nombre": datos.get("nombre", ""),
                "tipo": "rechazada" if motivo == RECHAZADA else "a_revisar",
                "motivo": motivo,
                "detalle": detalle,
            }
        )


def _existentes():
    """Escuelas del catálogo (incluidas las borradas) por ``codigo`` y por ``cue``."""
    por_clave = {}
    filas = Escuela.all_objects.values(
        "id", "codigo", "deleted_at", *CAMPOS_ACTUALIZABLES
    )
    for fila in filas:
        if fila["cue"]:
            por_clave.setdefault(fila["cue"], fila)
        por_clave[fila["codigo"]] = fila
    return por_clave


def _datos_de_fila(fila):
    return {
        "cueanexo": normalizar_cueanexo(fila.get("cueanexo")),
        "cueanexo_original": _texto(fila.get("cueanexo"), 40),
        "nombre": _texto(fila.get("nombre"), 255),
        "jurisdiccion": _texto(fila.get("jurisdiccion"), 120),
        "localidad": _texto(fila.get("localidad"), 255),
        "domicilio": _texto(fila.get("domicilio"), 255),
        "cp": _texto(fila.get("cp"), 20).upper(),
        "telefono": _texto(fila.get("telefono"), 255),
        "mail": _texto(fila.get("mail"), 255),
    }


def _causa_rechazo(datos, provincia_id):
    if not datos["cueanexo"]:
        valor = datos["cueanexo_original"]
        return (
            f"Cueanexo inválido: '{valor}' (lleva 9 dígitos)."
            if valor
            else "Falta el Cueanexo."
        )
    if not datos["nombre"]:
        return "Falta el nombre de la escuela."
    if provincia_id is None:
        return f"Jurisdicción desconocida: '{datos['jurisdiccion']}'."
    return ""


def _detalle_localidad(resolucion, datos, provincia):
    if resolucion.motivo == Escuela.MotivoRevision.LOCALIDAD_REPETIDA:
        return (
            f"{datos['localidad']}: está en {resolucion.coincidencias} municipios "
            f"de {provincia}"
        )
    return f"{datos['localidad'] or '(sin localidad)'} ({provincia})"


def _localidad_conservada(existente, datos, provincia_id):
    """Vínculo que ya tenía la escuela (por ejemplo, corregido a mano).

    Se conserva si la importación no resuelve la localidad y el archivo trae
    el mismo texto original y la misma provincia que la vez anterior.
    """
    if (
        existente
        and existente["localidad_vinculada_id"]
        and existente["provincia_id"] == provincia_id
        and existente["localidad_original"] == datos["localidad"]
    ):
        return (
            existente["localidad_vinculada_id"],
            existente["localidad"],
            existente["distrito"],
        )
    return None


def _valores(datos, provincia_id, resolucion, existente):
    motivos = []
    conservada = _localidad_conservada(existente, datos, provincia_id)
    if resolucion.localidad is not None:
        localidad_id = resolucion.localidad.id
        texto, distrito = textos_de_ubicacion(resolucion.localidad)
    elif conservada:
        localidad_id, texto, distrito = conservada
    else:
        localidad_id = None
        motivos.append(resolucion.motivo)
        texto, distrito = textos_de_ubicacion(
            None,
            texto_original=datos["localidad"],
            distrito_anterior=existente["distrito"] if existente else "",
        )
    if not mail_valido(datos["mail"]):
        motivos.append(Escuela.MotivoRevision.MAIL_INVALIDO)
    return {
        "nombre": datos["nombre"],
        "cue": datos["cueanexo"],
        "provincia_id": provincia_id,
        "localidad_vinculada_id": localidad_id,
        "localidad": texto,
        "distrito": distrito,
        "domicilio": datos["domicilio"],
        "cp": datos["cp"],
        "telefono": datos["telefono"],
        "mail": datos["mail"],
        "jurisdiccion_original": datos["jurisdiccion"],
        "localidad_original": datos["localidad"],
        "a_revisar": bool(motivos),
        "motivos_revision": [str(m) for m in motivos],
    }


def _observar_revision(resultado, numero, datos, motivos, detalle_localidad):
    for motivo in motivos:
        resultado.motivos[motivo] += 1
        if motivo == Escuela.MotivoRevision.MAIL_INVALIDO:
            detalle = datos["mail"]
        else:
            detalle = detalle_localidad
        resultado.observar(numero, datos, ETIQUETA_MOTIVO.get(motivo, motivo), detalle)


def _clasificar(filas, mapa, existentes):
    """Decide qué pasa con cada fila (``(numero, datos normalizados)``)."""
    resultado = Clasificacion()
    vistos = {}
    for numero, datos in filas:
        resultado.total += 1
        provincia_id, equivalencia = mapa.provincia(datos["jurisdiccion"])
        causa = _causa_rechazo(datos, provincia_id)
        if not causa and datos["cueanexo"] in vistos:
            causa = (
                f"Cueanexo repetido en el archivo (ya está en la fila "
                f"{vistos[datos['cueanexo']]})."
            )
        if causa:
            resultado.rechazadas += 1
            resultado.observar(numero, datos, RECHAZADA, causa)
            continue
        vistos[datos["cueanexo"]] = numero
        provincia = mapa.nombres_provincia[provincia_id]
        if equivalencia:
            resultado.equivalencias[datos["jurisdiccion"]] = provincia
        existente = existentes.get(datos["cueanexo"])
        resolucion = mapa.localidad(provincia_id, datos["localidad"])
        valores = _valores(datos, provincia_id, resolucion, existente)
        if valores["a_revisar"]:
            _observar_revision(
                resultado,
                numero,
                datos,
                valores["motivos_revision"],
                _detalle_localidad(resolucion, datos, provincia),
            )
        if existente is None:
            categoria = "nueva"
            resultado.nuevas.append((datos["cueanexo"], valores))
        elif existente["deleted_at"] is not None or any(
            existente[c] != v for c, v in valores.items()
        ):
            categoria = "actualizada"
            resultado.actualizadas.append((existente["codigo"], valores))
        else:
            categoria = "sin_cambios"
        resultado.categorias[(categoria, valores["a_revisar"])] += 1
    return resultado


def leer_escuelas(archivo):
    """``(meta, filas)``: el encabezado reconocido y las filas normalizadas.

    Las filas normalizadas son JSON: se guardan con la subida y la
    confirmación no vuelve a leer el ``.xlsx``.
    """
    planilla = leer_planilla(archivo, archivo.name, ALIAS, REQUERIDAS)
    meta = {"fila_encabezado": planilla.fila_encabezado, "columnas": planilla.columnas}
    return meta, [(numero, _datos_de_fila(fila)) for numero, fila in planilla.filas]


def resumen(meta, clasificacion):
    """Lo que muestra la revisión y se guarda con la subida (JSON).

    ``nuevas_sin_observaciones``, ``actualizadas_sin_observaciones``,
    ``sin_cambios``, ``a_revisar`` y ``rechazadas`` no se superponen: suman el
    total de filas. ``nuevas`` y ``actualizadas`` cuentan también las que
    quedan a revisar.
    """
    categorias = clasificacion.categorias
    return {
        "total": clasificacion.total,
        "fila_encabezado": meta["fila_encabezado"],
        "columnas": [
            {
                "original": c["original"],
                "campo": ETIQUETAS_COLUMNA.get(c["campo"], c["campo"]),
                "renombrada": c["campo"] == "jurisdiccion",
            }
            for c in meta["columnas"]
        ],
        "nuevas": len(clasificacion.nuevas),
        "actualizadas": len(clasificacion.actualizadas),
        "nuevas_sin_observaciones": categorias[("nueva", False)],
        "actualizadas_sin_observaciones": categorias[("actualizada", False)],
        "sin_cambios": categorias[("sin_cambios", False)],
        "a_revisar": sum(n for (_c, revisar), n in categorias.items() if revisar),
        "motivos": [
            {"codigo": codigo, "etiqueta": ETIQUETA_MOTIVO[codigo], "cantidad": n}
            for codigo, n in sorted(
                clasificacion.motivos.items(), key=lambda item: -item[1]
            )
        ],
        "rechazadas": clasificacion.rechazadas,
        "a_importar": len(clasificacion.nuevas) + len(clasificacion.actualizadas),
        "equivalencias": [
            {"desde": desde, "hacia": hacia}
            for desde, hacia in sorted(clasificacion.equivalencias.items())
        ],
    }


def _upsert(cursor, campos, actualizables, filas):
    """``INSERT`` de varias filas que actualiza la escuela si el ``codigo`` existe.

    El sufijo (``ON DUPLICATE KEY UPDATE`` en MySQL, ``ON CONFLICT`` en
    SQLite) lo arma el backend de Django, igual que en
    ``bulk_create(update_conflicts=True)``.
    """
    ops = connection.ops
    tabla = ops.quote_name(Escuela._meta.db_table)
    columnas = ", ".join(ops.quote_name(campo.column) for campo in campos)
    marcas = "(" + ", ".join(["%s"] * len(campos)) + ")"
    sufijo = ops.on_conflict_suffix_sql(
        campos,
        OnConflict.UPDATE,
        [campo.column for campo in actualizables],
        [Escuela._meta.get_field("codigo").column],
    )
    sql = (
        f"INSERT INTO {tabla} ({columnas}) VALUES "
        + ", ".join([marcas] * len(filas))
        + f" {sufijo}"
    )
    cursor.execute(sql, [valor for fila in filas for valor in fila])


def _guardar(clasificacion):
    """Guarda nuevas y actualizadas en lotes, en una transacción.

    Es SQL directo y no ``bulk_create``/``bulk_update`` por rendimiento: con
    el padrón (64.500 filas) el ORM tarda bastante más en preparar los
    objetos, y ``bulk_update`` (un ``CASE`` por campo) tardó casi un minuto.
    """
    meta = Escuela._meta
    ahora = connection.ops.adapt_datetimefield_value(timezone.now())
    motivos = meta.get_field("motivos_revision")
    actualizables = [
        meta.get_field(c)
        for c in (
            *CAMPOS_ACTUALIZABLES,
            "deleted_at",
            "deleted_by_id",
            "actualizada_at",
        )
    ]
    campos = [
        meta.get_field("codigo"),
        *actualizables,
        meta.get_field("nivel"),
        meta.get_field("creada_at"),
    ]
    # Los valores ya son texto, números, booleanos o None; sólo el JSON y las
    # fechas necesitan la conversión del backend.
    filas = [
        (
            codigo,
            *(
                (
                    motivos.get_db_prep_save(valores[c], connection)
                    if c == "motivos_revision"
                    else valores[c]
                )
                for c in CAMPOS_ACTUALIZABLES
            ),
            None,
            None,
            ahora,
            "",
            ahora,
        )
        for codigo, valores in (*clasificacion.nuevas, *clasificacion.actualizadas)
    ]
    lote = max(1, min(LOTE, connection.ops.bulk_batch_size(campos, filas)))
    with transaction.atomic(), connection.cursor() as cursor:
        for inicio in range(0, len(filas), lote):
            _upsert(cursor, campos, actualizables, filas[inicio : inicio + lote])


def _clasificar_contra_la_base(filas):
    return _clasificar(filas, MapaGeografico.cargar(), _existentes())


def analizar_escuelas(archivo):
    """Revisión, sin escribir en la base.

    Devuelve ``{"resumen", "observaciones", "datos"}``; ``datos`` (JSON) es lo
    que necesita ``aplicar_escuelas`` para confirmar sin releer el archivo.
    """
    meta, filas = leer_escuelas(archivo)
    clasificacion = _clasificar_contra_la_base(filas)
    return {
        "resumen": resumen(meta, clasificacion),
        "observaciones": clasificacion.observaciones,
        "datos": {"meta": meta, "filas": filas},
    }


def aplicar_escuelas(datos):
    """Confirmación: vuelve a clasificar contra la base actual y guarda.

    ``datos`` es el que devolvió ``analizar_escuelas`` (o su copia en JSON).
    """
    clasificacion = _clasificar_contra_la_base(datos["filas"])
    _guardar(clasificacion)
    return resumen(datos["meta"], clasificacion), clasificacion.observaciones
