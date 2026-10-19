"""Versiones del formulario: etiquetas y opciones que se guardan con cada acta."""

import json
from functools import lru_cache
from pathlib import Path

DIRECTORIO = Path(__file__).resolve().parent.parent / "formularios"
VERSION_ACTUAL = "v1"


@lru_cache(maxsize=None)
def _cargar(version):
    ruta = DIRECTORIO / f"{version}.json"
    with ruta.open(encoding="utf-8") as archivo:
        return json.load(archivo)


def versiones_disponibles():
    return sorted(p.stem for p in DIRECTORIO.glob("v*.json"))


def es_version_valida(version):
    return isinstance(version, str) and version in versiones_disponibles()


def obtener_formulario(version):
    """Definición de la versión (copia: quien la usa puede guardarla)."""
    return json.loads(json.dumps(_cargar(version)))


def turnos_validos(version=VERSION_ACTUAL):
    return [t["valor"] for t in _cargar(version)["turnos"]]


def limites(version=VERSION_ACTUAL):
    return dict(_cargar(version)["limites"])
