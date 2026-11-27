"""Alcance del usuario autenticado para la política de Celiaquía."""

from dashboard.models import ConfiguracionTableroInterno
from dashboard.services.alcance import alcance_efectivo


def alcance_celiaquia(usuario):
    configuracion = (
        ConfiguracionTableroInterno.objects.select_related("tablero")
        .filter(codigo="celiaquia", activa=True)
        .first()
    )
    if configuracion is None:
        return {"estado": "inactiva"}
    tablero = configuracion.tablero
    # Solo se admite la ruta canónica: ni orígenes ni aliases controlados por cliente.
    if not tablero.activo or tablero.ruta_interna != "/celiaquia/tablero/":
        return None
    alcance = alcance_efectivo(usuario, tablero)
    if alcance.nacional:
        return {"estado": "nacional"}
    if alcance.provincias:
        return {"estado": "provincial", "provincias": sorted(alcance.provincias)}
    return {"estado": "denegado"}
