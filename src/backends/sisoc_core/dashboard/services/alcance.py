"""Calcula concesiones explícitas sin alterar la política de tableros legacy."""

from dataclasses import dataclass

from django.db.models import Q

from dashboard.models import ConcesionTablero


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
    concesiones = (
        ConcesionTablero.objects.filter(tablero=tablero)
        .filter(Q(usuario=usuario) | Q(audiencia__membresias__usuario=usuario))
        .values_list("tipo", "provincia_id", "cdi_id")
        .distinct()
    )
    nacional = False
    provincias = set()
    cdis = set()
    for tipo, provincia_id, cdi_id in concesiones:
        if tipo == ConcesionTablero.Tipo.NACIONAL:
            nacional = True
        elif tipo == ConcesionTablero.Tipo.PROVINCIA and provincia_id:
            provincias.add(provincia_id)
        elif tipo == ConcesionTablero.Tipo.CDI and cdi_id:
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
