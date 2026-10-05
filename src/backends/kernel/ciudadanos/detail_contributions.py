"""Registro de contextos aportados por dominios a Ciudadano 360.

Hay dos tipos de contribución:

- **De contexto**: devuelven variables que usa ``ciudadano_detail.html``. Son
  las de apps que viven en el core (comedores, centrodefamilia, pwa).
- **Renderizadas**: además declaran su template. El detalle las inserta ya
  renderizadas (``contribuciones_html``), así funcionan igual si el dueño del
  dato corre en otro backend (src/backends/config/backends.json, ``ciudadano_contributions``):
  el core pide el fragmento al backend con la sesión del usuario.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

import requests
from django.conf import settings
from django.template.loader import render_to_string

from core.backend_proxy import outbound_headers

ContribucionDetalleCiudadano = Callable[[Any, Any], dict[str, Any]]

_CONTRIBUCIONES: dict[str, ContribucionDetalleCiudadano] = {}
_PLANTILLAS: dict[str, str] = {}

TIMEOUT_FRAGMENTO_SEGUNDOS = 4
logger_modulo = logging.getLogger("django")


def registrar_contribucion_detalle(
    nombre: str,
    contribucion: ContribucionDetalleCiudadano,
    plantilla: str | None = None,
) -> None:
    """Registra una contribucion determinista e idempotente.

    Con ``plantilla`` la contribución es renderizada: ver docstring del módulo.
    """
    existente = _CONTRIBUCIONES.get(nombre)
    if existente is None or existente is contribucion:
        _CONTRIBUCIONES[nombre] = contribucion
        if plantilla:
            _PLANTILLAS[nombre] = plantilla
        return
    raise ValueError(f"La contribucion de Ciudadano 360 '{nombre}' ya existe.")


def obtener_contexto_contribucion(
    nombre: str,
    ciudadano: Any,
    logger: Any,
    fallback: Callable[[], dict[str, Any]],
) -> dict[str, Any]:
    """Resuelve una contribucion registrada sin importar su implementacion."""
    contribucion = _CONTRIBUCIONES.get(nombre)
    return contribucion(ciudadano, logger) if contribucion else fallback()


def es_contribucion_local(nombre: str) -> bool:
    return nombre in _CONTRIBUCIONES and nombre in _PLANTILLAS


def renderizar_contribucion_local(nombre: str, request, ciudadano, logger) -> str:
    contexto = _CONTRIBUCIONES[nombre](ciudadano, logger)
    return render_to_string(
        _PLANTILLAS[nombre], {**contexto, "ciudadano": ciudadano}, request=request
    )


def _backend_de_contribucion(nombre: str):
    for spec in getattr(settings, "SISOC_BACKENDS", {}).values():
        if nombre in spec.get("ciudadano_contributions", ()):
            return spec
    return None


def _fragmento_remoto(request, spec, nombre: str, ciudadano_pk: int) -> str:
    url = (
        spec["origin"].rstrip("/")
        + f"/ciudadanos/{ciudadano_pk}/contribucion/{nombre}/"
    )
    try:
        respuesta = requests.get(
            url,
            headers=outbound_headers(request),
            timeout=TIMEOUT_FRAGMENTO_SEGUNDOS,
            allow_redirects=False,
        )
    except requests.RequestException:
        logger_modulo.warning("Contribución %s no disponible (%s)", nombre, url)
        return ""
    if respuesta.status_code != 200:
        logger_modulo.warning(
            "Contribución %s respondió %s (%s)", nombre, respuesta.status_code, url
        )
        return ""
    return respuesta.text


def renderizar_contribucion(nombre: str, request, ciudadano, logger) -> str:
    """HTML de una contribución renderizada, local o del backend dueño.

    Devuelve "" si no está disponible: el detalle muestra el resto igual.
    """
    if es_contribucion_local(nombre):
        return renderizar_contribucion_local(nombre, request, ciudadano, logger)
    spec = _backend_de_contribucion(nombre)
    if spec is None:
        return ""
    return _fragmento_remoto(request, spec, nombre, ciudadano.pk)
