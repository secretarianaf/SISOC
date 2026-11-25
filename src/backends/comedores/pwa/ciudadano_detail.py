"""Contribucion de PWA al detalle Ciudadano 360."""

from typing import Any

from ciudadanos.detail_contributions import (
    registrar_contribucion_detalle,
    registrar_proyector_aporte,
)
from pwa.models import NominaEspacioPWA


def obtener_contexto(ciudadano: Any, _logger: Any) -> dict[str, Any]:
    perfiles = NominaEspacioPWA.objects.filter(
        nomina__ciudadano=ciudadano,
        activo=True,
    )
    return {
        "pertenece_comunidad_indigena": perfiles.filter(
            pertenece_comunidad_indigena=True
        ).exists(),
        "situacion_calle_pwa": perfiles.filter(situacion_calle=True).exists(),
        "persona_con_celiaquia_pwa": perfiles.filter(
            persona_con_celiaquia=True
        ).exists(),
    }


def proyectar_aporte(ciudadano: Any) -> dict[str, Any]:
    """Seccion ``pwa`` en JSON; la consulta ya propaga sus excepciones."""
    contexto = obtener_contexto(ciudadano, None)
    return {
        "pwa": {
            "pertenece_comunidad_indigena": contexto["pertenece_comunidad_indigena"],
            "situacion_calle": contexto["situacion_calle_pwa"],
            "persona_con_celiaquia": contexto["persona_con_celiaquia_pwa"],
        }
    }


def registrar_contribucion_ciudadano() -> None:
    registrar_contribucion_detalle("pwa", obtener_contexto, "pwa/ciudadano_flags.html")
    registrar_contribucion_detalle(
        "pwa_badges", obtener_contexto, "pwa/ciudadano_badges.html"
    )
    registrar_proyector_aporte("pwa", proyectar_aporte)
