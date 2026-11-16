"""Alcance por programa de comedores (PNUD / Alimentar comunidad).

Es un eje independiente del territorio y de los equipos técnicos: se aplica
con AND sobre el alcance que ya tenga el usuario. Solo el superusuario lo
saltea. Ver ``docs/registro/decisiones/2026-11-16-alcance-programa-comedores.md``.
"""

from comedores.models import AlcanceProgramaComedor, Programas
from comedores.utils import (
    es_programa_alimentar_comunidad,
    es_programa_linea_secos,
    es_programa_linea_tradicional,
)

PNUD = AlcanceProgramaComedor.PNUD
ALIMENTAR_COMUNIDAD = AlcanceProgramaComedor.ALIMENTAR_COMUNIDAD
TODOS_LOS_GRUPOS = frozenset({PNUD, ALIMENTAR_COMUNIDAD})

_CACHE_ATTR = "_alcance_programa_cache"


def grupo_de_programa(programa):
    """Grupo de negocio de un ``Programas`` o ``None`` si no pertenece a ninguno."""
    if es_programa_alimentar_comunidad(programa):
        return ALIMENTAR_COMUNIDAD
    if es_programa_linea_secos(programa) or es_programa_linea_tradicional(programa):
        return PNUD
    return None


def _grupos_configurados(user):
    profile = getattr(user, "profile", None)
    if profile is None or not getattr(profile, "pk", None):
        return frozenset()
    return frozenset(
        AlcanceProgramaComedor.objects.filter(profile_id=profile.pk).values_list(
            "programa", flat=True
        )
    )


def programas_visibles(user):
    """Grupos de programa que el usuario puede ver, o ``None`` si no tiene restricción.

    Sin nada tildado o con ambos grupos tildados no hay restricción. Se cachea
    en la instancia del usuario (una por request) para no repetir la consulta.
    """
    if not user or getattr(user, "is_superuser", False):
        return None
    if not getattr(user, "is_authenticated", True):
        return None
    cached = getattr(user, _CACHE_ATTR, False)
    if cached is not False:
        return cached
    grupos = _grupos_configurados(user)
    resultado = None if not grupos or grupos >= TODOS_LOS_GRUPOS else grupos
    try:
        setattr(user, _CACHE_ATTR, resultado)
    except AttributeError:  # pragma: no cover - usuarios que no admiten atributos
        pass
    return resultado


def invalidar_cache_alcance_programa(user):
    if hasattr(user, _CACHE_ATTR):
        delattr(user, _CACHE_ATTR)


def programa_ids_por_grupos(grupos):
    """Ids de ``Programas`` que pertenecen a los grupos dados (por nombre)."""
    return [
        programa.pk
        for programa in Programas.objects.only("id", "nombre")
        if grupo_de_programa(programa) in grupos
    ]


def apply_programa_scope(queryset, user, lookup="programa"):
    """Acota ``queryset`` a los programas visibles del usuario.

    ``lookup`` es la ruta al programa desde el modelo del queryset (por
    ejemplo ``"comedor__programa"``). Los comedores sin programa o de otro
    programa solo los ven usuarios sin restricción.
    """
    grupos = programas_visibles(user)
    if grupos is None:
        return queryset
    return queryset.filter(**{f"{lookup}_id__in": programa_ids_por_grupos(grupos)})
