"""Definicion de los formularios PNUD (N22) para mostrar las respuestas.

``data/pnud_formularios.json`` se genera desde la app territorial, que es la
fuente de los formularios (``pwa/src/features/pnud/pnudForm.ts`` del repo
Gestionar): secciones y campos en el orden del formulario en papel, con su
etiqueta, tipo, opciones y columnas de las tablas. Si la app cambia un
formulario, se regenera ejecutando ``buildPnudForm(id)`` para los cinco ids
(``secos``, ``iia1``, ``iib1``, ``iia``, ``iib``) y volcando el resultado a
JSON (ver el PR de N22).
"""

import json
from datetime import date, datetime
from functools import lru_cache
from pathlib import Path

_RUTA = Path(__file__).resolve().parent / "data" / "pnud_formularios.json"


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


def formatear_valor(campo, valor):  # pylint: disable=too-many-return-statements
    """Valor de una respuesta como texto legible según el tipo del campo."""
    if _vacio(valor):
        return "—"
    if valor is True:
        return "Sí"
    if valor is False:
        return "No"
    tipo = campo.get("type")
    if tipo == "enumlist" or isinstance(valor, list):
        items = valor if isinstance(valor, list) else [valor]
        return ", ".join(_opcion(campo, item) for item in items)
    if tipo in ("enum", "ref"):
        return _opcion(campo, valor)
    if tipo == "date":
        return _fecha(valor, con_hora=False)
    if tipo == "datetime":
        return _fecha(valor, con_hora=True)
    if isinstance(valor, dict):
        return ", ".join(f"{_humanizar(k)}: {v}" for k, v in valor.items())
    return str(valor)


def _fila(campo, valor):
    etiqueta = campo["label"]
    if campo.get("type") == "child":
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
    if campo.get("type") == "signature":
        return {"etiqueta": etiqueta, "tipo": "imagen", "valor": valor}
    return {
        "etiqueta": etiqueta,
        "tipo": "texto",
        "valor": formatear_valor(campo, valor),
    }


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
        filas = []
        for campo in seccion["fields"]:
            usadas.add(campo["name"])
            valor = datos.get(campo["name"])
            if _vacio(valor):
                continue
            filas.append(_fila(campo, valor))
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
