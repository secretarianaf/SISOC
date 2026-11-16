"""Alcance por programa de comedores (PNUD / Alimentar comunidad).

Es un eje independiente del territorio y de los equipos técnicos: se aplica
con AND sobre el alcance que ya tenga el usuario. Solo el superusuario lo
saltea. Ver ``docs/registro/decisiones/2026-11-16-alcance-programa-comedores.md``.
"""

from django.db.models.signals import post_delete, post_save

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


_IDS_POR_GRUPO_CACHE = None


def _limpiar_cache_ids_por_grupo(**_kwargs):
    global _IDS_POR_GRUPO_CACHE
    _IDS_POR_GRUPO_CACHE = None


post_save.connect(
    _limpiar_cache_ids_por_grupo,
    sender=Programas,
    dispatch_uid="alcance_programa.programas_post_save",
)
post_delete.connect(
    _limpiar_cache_ids_por_grupo,
    sender=Programas,
    dispatch_uid="alcance_programa.programas_post_delete",
)


def programa_ids_por_grupos(grupos):
    """Ids de ``Programas`` que pertenecen a los grupos dados (por nombre).

    El mapa grupo -> ids se cachea a nivel de módulo y se invalida al guardar
    o borrar un ``Programas``, así no se recorre la tabla en cada consulta.
    """
    global _IDS_POR_GRUPO_CACHE
    mapa = _IDS_POR_GRUPO_CACHE
    if mapa is None:
        mapa = {grupo: [] for grupo in TODOS_LOS_GRUPOS}
        for programa in Programas.objects.only("id", "nombre"):
            grupo = grupo_de_programa(programa)
            if grupo is not None:
                mapa[grupo].append(programa.pk)
        _IDS_POR_GRUPO_CACHE = mapa
    return [pk for grupo in grupos for pk in mapa.get(grupo, ())]


def comedor_en_alcance_programa(user, comedor):
    """``True`` si el comedor es visible para el usuario según su programa."""
    grupos = programas_visibles(user)
    if grupos is None:
        return True
    programa_id = getattr(comedor, "programa_id", None)
    return programa_id is not None and programa_id in programa_ids_por_grupos(grupos)


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
