"""Calcula las concesiones explícitas por usuario y tablero."""

from dataclasses import dataclass

from django.apps import apps
from django.db.models import Q


@dataclass(frozen=True)
class AlcanceTablero:
    puede_ver: bool = False
    nacional: bool = False
    provincias: frozenset = frozenset()
    cdis: frozenset = frozenset()


def alcance_efectivo(usuario, tablero, *, validar_cdis=None):
    """Sin un validador de CDI, no se conceden alcances de ese tipo."""
    if (
        not usuario
        or not usuario.is_authenticated
        or not usuario.is_active
        or not tablero.activo
    ):
        return AlcanceTablero()
    modelo = apps.get_model("dashboard", "ConcesionTablero")
    concesiones = (
        _concesiones_de_usuario(modelo, usuario)
        .filter(tablero=tablero)
        .values_list("tipo", "provincia_id", "cdi_id")
        .distinct()
    )
    nacional = False
    provincias = set()
    cdis = set()
    for tipo, provincia_id, cdi_id in concesiones:
        if tipo == modelo.Tipo.NACIONAL:
            nacional = True
        elif tipo == modelo.Tipo.PROVINCIA and provincia_id:
            provincias.add(provincia_id)
        elif tipo == modelo.Tipo.CDI and cdi_id:
            cdis.add(cdi_id)
    if cdis:
        cdis = (
            cdis.intersection(validar_cdis(frozenset(cdis))) if validar_cdis else set()
        )
    return AlcanceTablero(
        bool(nacional or provincias or cdis),
        nacional,
        frozenset(provincias),
        frozenset(cdis),
    )


def _concesiones_de_usuario(modelo, usuario):
    return modelo.objects.filter(
        Q(usuario=usuario) | Q(audiencia__membresias__usuario=usuario)
    )


def concesiones_nacionales(usuario):
    modelo = apps.get_model("dashboard", "ConcesionTablero")
    if not usuario or not usuario.is_authenticated or not usuario.is_active:
        return modelo.objects.none()
    return _concesiones_de_usuario(modelo, usuario).filter(tipo=modelo.Tipo.NACIONAL)
