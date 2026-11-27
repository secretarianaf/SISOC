"""Presentación honesta del alcance efectivamente soportado por tablero."""

from dashboard.models import ConcesionTablero
from dashboard.services.politicas import (
    RUTA_CELIAQUIA,
    configuracion_celiaquia,
    es_embed_externo,
    es_ruta_progresar,
)


def marcar_estado_concesiones(concesiones, configuracion):
    """Distingue configuración guardada de política efectivamente integrada."""
    resultado = list(concesiones)
    celiaquia = configuracion_celiaquia()
    tableros_internos = {
        politica.tablero_id for politica in (configuracion, celiaquia) if politica
    }
    for concesion in resultado:
        concesion.entrada_embed_habilitada = (
            concesion.tipo == ConcesionTablero.Tipo.NACIONAL
            and concesion.tablero.activo
            and concesion.tablero_id not in tableros_internos
            and es_embed_externo(concesion.tablero)
        )
        concesion.politica_aplicada = bool(
            concesion.tablero.activo
            and (
                (
                    configuracion
                    and configuracion.tablero_id == concesion.tablero_id
                    and es_ruta_progresar(concesion.tablero.ruta_interna)
                )
                or (
                    celiaquia
                    and celiaquia.tablero_id == concesion.tablero_id
                    and concesion.tablero.ruta_interna == RUTA_CELIAQUIA
                )
            )
            and concesion.tipo
            in (ConcesionTablero.Tipo.NACIONAL, ConcesionTablero.Tipo.PROVINCIA)
        )
    return resultado
