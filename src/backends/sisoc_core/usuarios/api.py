"""Compatibilidad de la fachada de accesos trasladada a Espacios comunitarios.

Los consumidores de negocio usan pwa.api. Se conserva este import público
durante la preparación de la extracción, sin duplicar lógica de accesos.
"""

from pwa.api import (
    aplicar_cambio_organizacion_comedor,
    obtener_ids_organizaciones_con_acceso_pwa,
    previsualizar_accesos_organizacion,
    sincronizar_accesos_organizacion,
)

__all__ = [
    "aplicar_cambio_organizacion_comedor",
    "obtener_ids_organizaciones_con_acceso_pwa",
    "previsualizar_accesos_organizacion",
    "sincronizar_accesos_organizacion",
]
