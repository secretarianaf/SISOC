"""Definicion de los formularios PNUD (N22) para mostrar las respuestas.

``data/pnud_formularios.json`` se genera desde la app territorial, que es la
fuente de los formularios (``pwa/src/features/pnud/pnudForm.ts`` del repo
Gestionar): secciones y campos en el orden del formulario en papel, con su
etiqueta, tipo, opciones, columnas de las tablas y, en los Sí/No que el papel
escribe distinto, ``etiquetasSiNo``. El primer campo de cada bloque con
subtítulo en el papel ("3.4 Detalle del menú…") lo trae en ``titulo``. Las
preguntas que se ordenan (ranking) o
se marcan con cruz (casillas) llegan aplanadas: un campo por cada clave que
guardan en ``datos``. Las etiquetas son las
literales del documento "FLUJO APP PNUD" §7.2; los ``name`` y los ``value``
de las opciones son las claves guardadas en ``datos`` y no cambian. Si la app
cambia un formulario, se regenera desde ``pwa/`` del repo Gestionar con
``node scripts/pnud/formularios-json.mjs <ruta a este JSON>``.
"""

import json
import re
from datetime import date, datetime
from functools import lru_cache
from pathlib import Path

_RUTA = Path(__file__).resolve().parent / "data" / "pnud_formularios.json"

# Numeración del papel al inicio de una etiqueta o subtítulo: "3.6 ", "7.1.1 ".
_NUMERO = re.compile(r"^(\d+(?:\.\d+)+)\s")


@lru_cache(maxsize=1)
def definiciones():
    with _RUTA.open(encoding="utf-8") as archivo:
        return json.load(archivo)


def _vacio(valor):
    return valor is None or valor == "" or valor == [] or valor == {}


def _humanizar(clave):
    return clave.replace("_", " ").capitalize()


def _fecha(valor, con_hora):
    try:
        if con_hora:
            return datetime.fromisoformat(str(valor)).strftime("%d/%m/%Y %H:%M")
        return date.fromisoformat(str(valor)[:10]).strftime("%d/%m/%Y")
    except ValueError:
        return str(valor)


def _opcion(campo, valor):
    for opcion in campo.get("options") or []:
        if str(opcion["value"]) == str(valor):
            return opcion["label"]
    return str(valor)


def campos_tabla(formulario):
    """Nombres de los campos tabla (filas hijas) del formulario."""
    definicion = definiciones().get(formulario) or {"sections": []}
    return [
        campo["name"]
        for seccion in definicion["sections"]
        for campo in seccion["fields"]
        if campo.get("type") == "child"
    ]


def opciones_exclusivas(formulario):
    """{campo: opción} de los campos de elección múltiple con una opción exclusiva
    (p. ej. "Ninguna": no se puede combinar con otras)."""
    definicion = definiciones().get(formulario) or {"sections": []}
    return {
        campo["name"]: campo["opcionExclusiva"]
        for seccion in definicion["sections"]
        for campo in seccion["fields"]
        if campo.get("opcionExclusiva")
    }


def formatear_valor(campo, valor):  # pylint: disable=too-many-return-statements
    """Valor de una respuesta como texto legible según el tipo del campo."""
    if _vacio(valor):
        return "—"
    if isinstance(valor, bool):
        # El papel escribe algunas respuestas "SI/NO" (sin tilde): el JSON lo trae
        # en ``etiquetasSiNo``; si no, Sí/No.
        si, no = campo.get("etiquetasSiNo") or ("Sí", "No")
        return si if valor else no
    if isinstance(valor, dict):
        partes = [
            f"{_humanizar(str(clave))}: {formatear_valor({}, item)}"
            for clave, item in valor.items()
            if not _vacio(item)
        ]
        return ", ".join(partes) or "—"
    tipo = campo.get("type")
    if tipo == "enumlist" or isinstance(valor, list):
        items = valor if isinstance(valor, list) else [valor]
        separador = " · " if any(isinstance(i, (dict, list)) for i in items) else ", "
        return separador.join(
            (
                formatear_valor({}, item)
                if isinstance(item, (dict, list))
                else _opcion(campo, item)
            )
            for item in items
        )
    if tipo in ("enum", "ref"):
        return _opcion(campo, valor)
    if tipo == "date":
        return _fecha(valor, con_hora=False)
    if tipo == "datetime":
        return _fecha(valor, con_hora=True)
    return str(valor)


def _es_url_mostrable(valor):
    """Solo http(s) o rutas relativas del sitio se renderizan como <img>."""
    return isinstance(valor, str) and (
        valor.startswith(("https://", "http://"))
        or (valor.startswith("/") and not valor.startswith("//"))
    )


def _fila(campo, valor):
    etiqueta = campo["label"]
    if campo.get("type") == "child" and isinstance(valor, list):
        columnas = campo.get("itemFields") or []
        filas = [
            [
                formatear_valor(columna, fila.get(columna["name"]))
                for columna in columnas
            ]
            for fila in valor
            if isinstance(fila, dict)
        ]
        return {
            "etiqueta": etiqueta,
            "tipo": "tabla",
            "columnas": [columna["label"] for columna in columnas],
            "filas": filas,
        }
    if campo.get("type") == "signature" and _es_url_mostrable(valor):
        return {"etiqueta": etiqueta, "tipo": "imagen", "valor": valor}
    return {
        "etiqueta": etiqueta,
        "tipo": "texto",
        "valor": formatear_valor(campo, valor),
    }


def _sale_del_bloque(subtitulo, etiqueta):
    """True si la etiqueta abre otra pregunta numerada fuera del bloque del subtítulo.

    Bajo "3.5 Indique el menú…", "3.6 ¿Cuentan con menú planificado?" ya es otra
    pregunta; bajo "7.1 Seguridad e higiene", "7.1.2 …" sigue en el bloque.
    """
    propio = _NUMERO.match(etiqueta or "")
    if not propio:
        return False
    bloque = _NUMERO.match(subtitulo)
    return not bloque or not propio.group(1).startswith(bloque.group(1) + ".")


def _filas_de_seccion(seccion, datos, usadas):
    """Filas respondidas de una sección; cada subtítulo del papel va antes de la
    primera respuesta de su bloque (si el bloque quedó vacío, no se muestra)."""
    filas = []
    subtitulo = None
    for campo in seccion["fields"]:
        usadas.add(campo["name"])
        if subtitulo and _sale_del_bloque(subtitulo, campo["label"]):
            subtitulo = None
        if campo.get("titulo"):
            subtitulo = campo["titulo"]
        valor = datos.get(campo["name"])
        if _vacio(valor):
            continue
        if subtitulo:
            filas.append({"etiqueta": subtitulo, "tipo": "subtitulo"})
            subtitulo = None
        filas.append(_fila(campo, valor))
    return filas


def respuestas_por_seccion(formulario, datos):
    """Secciones del formulario con las respuestas cargadas, en su orden.

    Solo se listan los campos respondidos (los condicionales no recorridos no
    aparecen). Las claves que no están en la definición se agregan al final en
    "Otros datos" para no ocultar información.
    """
    datos = datos or {}
    definicion = definiciones().get(formulario) or {"sections": []}
    usadas = set()
    secciones = []
    for seccion in definicion["sections"]:
        filas = _filas_de_seccion(seccion, datos, usadas)
        if filas:
            secciones.append({"titulo": seccion["title"], "filas": filas})
    otros = [
        {
            "etiqueta": _humanizar(clave),
            "tipo": "texto",
            "valor": formatear_valor({}, valor),
        }
        for clave, valor in datos.items()
        if clave not in usadas and not _vacio(valor)
    ]
    if otros:
        secciones.append({"titulo": "Otros datos", "filas": otros})
    return secciones


def titulos(formulario):
    definicion = definiciones().get(formulario) or {}
    return {"linea": definicion.get("linea"), "titulo": definicion.get("titulo")}
