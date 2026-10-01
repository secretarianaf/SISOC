"""Busqueda de destinatarios para el armado de comunicados (issue #2505).

Reutiliza los motores de filtros combinables de los listados de comedores y
organizaciones, acotando siempre el universo al alcance del usuario.

La busqueda en si vive en `comedores/api.py`, la fachada publica de Comedores
Core: el contrato `comedores-core-public-boundary` le prohibe a `comunicados`
importar `comedores.models`, `comedores.services` y `organizaciones.models`. De
este lado del limite solo circulan DTOs, nunca objetos del ORM.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List

from comedores.api import (
    buscar_comedores_para_destinatarios,
    buscar_organizaciones_para_destinatarios,
    get_filtros_destinatarios_config as _config_de_filtros_de_la_fachada,
    nombres_de_comedores,
    nombres_de_organizaciones,
)

from .permissions import (
    get_ids_comedores_del_usuario,
    get_ids_organizaciones_del_usuario,
    tiene_alcance_total_destinatarios,
)

# Tope de resultados que se listan por pagina en el panel de destinatarios.
PAGE_SIZE = 25

# Tope duro para "agregar todos los resultados": evita que un filtro vacio
# intente cargar decenas de miles de destinatarios en el formulario.
MAX_SELECCION_MASIVA = 2000


def _ids_scope_comedores(user):
    """Ids a los que se acota la busqueda, o ``None`` si el alcance es total.

    ``None`` no es "sin alcance": es alcance total, y le evita a la fachada
    armar un ``IN`` con todos los comedores del sistema.
    """

    if tiene_alcance_total_destinatarios(user):
        return None
    return get_ids_comedores_del_usuario(user)


def _ids_scope_organizaciones(user):
    if tiene_alcance_total_destinatarios(user):
        return None
    return get_ids_organizaciones_del_usuario(user)


def _ids_validos(ids) -> List[int]:
    """Descarta valores no numericos (p. ej. un POST manipulado)."""

    validos = []
    for pk in ids or []:
        try:
            validos.append(int(pk))
        except (TypeError, ValueError):
            continue
    return validos


def _respuesta_pagina(pagina, page: int) -> Dict[str, Any]:
    return {
        "results": [
            {"id": item.id, "nombre": item.nombre, "detalle": item.detalle}
            for item in pagina.items
        ],
        "total": pagina.total,
        "has_more": pagina.hay_mas,
        "page": max(1, page),
        "max_seleccion_masiva": MAX_SELECCION_MASIVA,
    }


def buscar_comedores(request, user, page: int = 1) -> Dict[str, Any]:
    """Comedores del usuario que matchean los filtros recibidos."""

    pagina = buscar_comedores_para_destinatarios(
        request,
        ids_scope=_ids_scope_comedores(user),
        page=page,
        page_size=PAGE_SIZE,
    )
    return _respuesta_pagina(pagina, page)


def buscar_organizaciones(request, user, page: int = 1) -> Dict[str, Any]:
    """Organizaciones del usuario que matchean los filtros recibidos."""

    pagina = buscar_organizaciones_para_destinatarios(
        request,
        ids_scope=_ids_scope_organizaciones(user),
        page=page,
        page_size=PAGE_SIZE,
    )
    return _respuesta_pagina(pagina, page)


def _respuesta_seleccion_masiva(pagina) -> Dict[str, Any]:
    """Convierte una pagina del tope en la respuesta de 'agregar todos'.

    Se pide una sola pagina de ``MAX_SELECCION_MASIVA`` elementos: si el total
    la supera, se corta sin haber traido las filas.
    """

    if pagina.total > MAX_SELECCION_MASIVA:
        return {
            "results": [],
            "total": pagina.total,
            "truncado": True,
            "max_seleccion_masiva": MAX_SELECCION_MASIVA,
        }
    return {
        "results": [{"id": item.id, "nombre": item.nombre} for item in pagina.items],
        "total": pagina.total,
        "truncado": False,
        "max_seleccion_masiva": MAX_SELECCION_MASIVA,
    }


def seleccionar_todos_comedores(request, user) -> Dict[str, Any]:
    """Todos los comedores que matchean, para el boton 'agregar todos'."""

    return _respuesta_seleccion_masiva(
        buscar_comedores_para_destinatarios(
            request,
            ids_scope=_ids_scope_comedores(user),
            page=1,
            page_size=MAX_SELECCION_MASIVA,
        )
    )


def seleccionar_todas_organizaciones(request, user) -> Dict[str, Any]:
    """Todas las organizaciones que matchean, para el boton 'agregar todos'."""

    return _respuesta_seleccion_masiva(
        buscar_organizaciones_para_destinatarios(
            request,
            ids_scope=_ids_scope_organizaciones(user),
            page=1,
            page_size=MAX_SELECCION_MASIVA,
        )
    )


def etiquetas_de_seleccion(user, comedor_ids: Iterable[int], organizacion_ids) -> Dict:
    """Nombres de los destinatarios ya seleccionados, para pintar los badges."""

    comedores = nombres_de_comedores(
        _ids_validos(comedor_ids), ids_scope=_ids_scope_comedores(user)
    )
    organizaciones = nombres_de_organizaciones(
        _ids_validos(organizacion_ids), ids_scope=_ids_scope_organizaciones(user)
    )
    return {
        "comedores": [{"id": item.id, "nombre": item.nombre} for item in comedores],
        "organizaciones": [
            {"id": item.id, "nombre": item.nombre} for item in organizaciones
        ],
    }


def get_filtros_destinatarios_config() -> Dict[str, Any]:
    """Config de filtros de ambos universos, para el panel de destinatarios."""

    return _config_de_filtros_de_la_fachada()


__all__ = [
    "PAGE_SIZE",
    "MAX_SELECCION_MASIVA",
    "buscar_comedores",
    "buscar_organizaciones",
    "seleccionar_todos_comedores",
    "seleccionar_todas_organizaciones",
    "etiquetas_de_seleccion",
    "get_filtros_destinatarios_config",
]
