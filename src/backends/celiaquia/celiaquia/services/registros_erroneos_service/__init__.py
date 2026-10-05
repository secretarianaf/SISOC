"""Compatibility alias that preserves original module patch semantics."""

import sys as _sys

# Reexport explicito, como `legajo_service`: en ejecucion el modulo es `impl`
# (ver abajo), pero pylint lee este archivo y sin esto no ve los nombres.
from .impl import (
    actualizar,
    campos_invalidos,
    eliminar,
    provincia_de,
    puede_gestionar,
    reprocesar,
)
from . import impl as _impl

__all__ = [
    "actualizar",
    "campos_invalidos",
    "eliminar",
    "provincia_de",
    "puede_gestionar",
    "reprocesar",
]

_sys.modules[__name__] = _impl
