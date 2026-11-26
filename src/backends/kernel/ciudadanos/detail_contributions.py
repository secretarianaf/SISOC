"""Registro de contextos aportados por dominios a Ciudadano 360.

Las contribuciones renderizadas conservan consulta y templates en su dueño.
El portal usa el mismo fragmento local o HTTP con la sesión original; una falla
remota omite sólo esa contribución. C2 declara propiedad por app; el registro del
backend Comedores y su runtime se incorporan en C3.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import datetime
from typing import Any

import requests
from django.conf import settings
from django.template.defaultfilters import date as date_filter
from django.template.loader import render_to_string
from django.utils import timezone

from core.backend_proxy import backend_de_app, outbound_headers

ContribucionDetalleCiudadano = Callable[[Any, Any], dict[str, Any]]

_CONTRIBUCIONES: dict[str, ContribucionDetalleCiudadano] = {}
_PLANTILLAS: dict[str, str] = {}

APPS_CONTRIBUCIONES = {
    "comedores": "comedores",
    "comedores_colaboraciones": "comedores",
    "pwa": "pwa",
    "pwa_badges": "pwa",
}

# Aportes JSON de la ficha React (C04): un endpoint por proveedor, no por bloque.
APORTES_WEB = {
    "comedores": ("comedores", "comedores_colaboraciones"),
    "pwa": ("pwa", "pwa_badges"),
    "celiaquia": ("celiaquia",),
    "vat": ("vat",),
    "centrodefamilia": ("centrodefamilia", "centrodefamilia_monto"),
}
ProyectorAporte = Callable[[Any], dict[str, Any]]
_PROYECTORES: dict[str, ProyectorAporte] = {}

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
    app_label = APPS_CONTRIBUCIONES.get(nombre)
    if app_label is not None:
        return backend_de_app(app_label)
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


def registrar_proyector_aporte(aporte: str, proyector: ProyectorAporte) -> None:
    """Registra el proyector JSON de un aporte; lo llama el dueño en ``ready()``.

    ``proyector(ciudadano)`` devuelve ``{sección: valor}`` y deja propagar
    cualquier excepción de su consulta (la vista responde 503).
    """
    if aporte not in APORTES_WEB:
        raise ValueError(f"El aporte '{aporte}' de Ciudadano 360 no existe.")
    existente = _PROYECTORES.get(aporte)
    if existente is None or existente is proyector:
        _PROYECTORES[aporte] = proyector
        return
    raise ValueError(f"El proyector del aporte '{aporte}' ya existe.")


def proyector_de_aporte(aporte: str) -> ProyectorAporte | None:
    return _PROYECTORES.get(aporte)


def nombre_backend_de_aporte(aporte: str) -> str | None:
    """Clave de ``backends.json`` del dueño del aporte, o ``None`` si no se resuelve.

    Con backends separados exige que el core lo tenga configurado
    (``SISOC_BACKENDS``, igual que ``_backend_de_contribucion``); en el
    monolito, donde no hay saltos remotos, el dueño es el de ``backends.json``.
    """
    from config.backends import (  # pylint: disable=import-outside-toplevel
        load_backends_registry,
    )

    seccion = APORTES_WEB[aporte][0]
    app_label = APPS_CONTRIBUCIONES.get(seccion)
    for nombre, spec in load_backends_registry().items():
        if (app_label and app_label in spec["apps"]) or seccion in spec.get(
            "ciudadano_contributions", ()
        ):
            configurados = getattr(settings, "SISOC_BACKENDS", {})
            if configurados and nombre not in configurados:
                return None
            return nombre
    return None


def aportes_web_de_ciudadano(ciudadano_pk: int) -> list[dict[str, Any]]:
    """Lista de aportes con su ruta JSON, armada en el servidor para la ficha React."""
    aportes = []
    for aporte, secciones in APORTES_WEB.items():
        backend = nombre_backend_de_aporte(aporte)
        if backend is None:
            continue
        aportes.append(
            {
                "aporte": aporte,
                "secciones": list(secciones),
                "url": f"/api/web/{backend}/ciudadanos/{ciudadano_pk}/aportes/{aporte}/",
            }
        )
    return aportes


def fecha_texto(valor: Any, formato: str = "d/m/Y", por_defecto: str = "") -> str:
    """Igual que ``{{ valor|date:formato|default:por_defecto }}`` en un template.

    Los datetime con zona se pasan a hora local antes de formatear, como hace
    el motor de templates al resolver la variable.
    """
    if valor in (None, ""):
        return por_defecto
    if isinstance(valor, datetime) and timezone.is_aware(valor):
        valor = timezone.localtime(valor)
    return date_filter(valor, formato) or por_defecto
