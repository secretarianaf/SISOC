"""Registro de ítems del menú lateral aportados por apps del core."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

ProveedorTableros = Callable[[Any], list]

_proveedor_tableros: ProveedorTableros | None = None


def registrar_proveedor_tableros(proveedor: ProveedorTableros) -> None:
    """Registra, una sola vez, quién arma los tableros del menú."""
    global _proveedor_tableros  # pylint: disable=global-statement
    if _proveedor_tableros is None or _proveedor_tableros is proveedor:
        _proveedor_tableros = proveedor
        return
    raise ValueError("Ya hay un proveedor de tableros registrado.")


def obtener_tableros(context) -> list:
    return _proveedor_tableros(context) if _proveedor_tableros else []
