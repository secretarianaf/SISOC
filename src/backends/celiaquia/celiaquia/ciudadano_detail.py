"""Contribución de Celiaquía al detalle Ciudadano 360."""

import logging
from typing import Any

from celiaquia.api import obtener_resumen_ciudadano
from ciudadanos.detail_contributions import (
    fecha_texto,
    registrar_contribucion_detalle,
    registrar_proyector_aporte,
)

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


def proyectar_aporte(ciudadano: Any) -> dict[str, Any]:
    """Seccion ``celiaquia`` en JSON; la consulta propaga sus excepciones."""
    resumen = obtener_resumen_ciudadano(ciudadano.pk)
    actual = resumen.legajo_actual
    return {
        "celiaquia": {
            "legajo_actual": (
                {
                    "estado_expediente": actual.estado_expediente,
                    "estado_legajo": actual.estado_legajo,
                    "resultado_cruce": actual.resultado_cruce,
                    "estado_cupo": actual.estado_cupo,
                    "es_titular_activo": actual.es_titular_activo,
                    "revision_tecnica": actual.revision_tecnica,
                }
                if actual
                else None
            ),
            "historial": [
                {
                    "estado_legajo": legajo.estado_legajo,
                    "estado_cupo": legajo.estado_cupo,
                    "creado_en_texto": fecha_texto(legajo.creado_en, "d/m/Y H:i"),
                }
                for legajo in resumen.historial
            ],
        }
    }


def registrar_contribucion_ciudadano() -> None:
    registrar_contribucion_detalle("celiaquia", obtener_contexto, PLANTILLA)
    registrar_proyector_aporte("celiaquia", proyectar_aporte)
