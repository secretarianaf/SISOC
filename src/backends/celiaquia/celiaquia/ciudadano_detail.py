"""Contribución de Celiaquía al detalle Ciudadano 360."""

import logging
from typing import Any

from celiaquia.api import obtener_resumen_ciudadano
from ciudadanos.detail_contributions import registrar_contribucion_detalle

PLANTILLA = "celiaquia/ciudadano_detalle_seccion.html"


def obtener_contexto(ciudadano: Any, logger: Any = None) -> dict[str, Any]:
    logger = logger or logging.getLogger("django")
    try:
        return {"celiaquia_resumen": obtener_resumen_ciudadano(ciudadano.pk)}
    except Exception:  # pylint: disable=broad-exception-caught
        logger.exception(
            "Error cargando expedientes celiaquia para ciudadano %s", ciudadano.pk
        )
        return {"celiaquia_resumen": None}


def registrar_contribucion_ciudadano() -> None:
    registrar_contribucion_detalle("celiaquia", obtener_contexto, PLANTILLA)
