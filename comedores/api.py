"""Contrato Python público de las capacidades compartidas de Comedores."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from django.db.models import Sum
from django.db.models.signals import post_delete, post_save

from comedores.models import Comedor, ValorComida
from core.soft_delete.signals import post_restore, post_soft_delete
from organizaciones.models import Organizacion


@dataclass(frozen=True)
class MetricasComedores:
    """Proyección de sólo lectura para consumidores externos del contexto."""

    cantidad_espacios: int
    presupuesto_desayuno: int | float
    presupuesto_merienda: int | float
    presupuesto_comida: int | float


def obtener_metricas_dashboard() -> MetricasComedores:
    """Devuelve los indicadores de Comedores que consume el Dashboard."""

    def _presupuesto(tipo: str):
        return (
            ValorComida.objects.filter(tipo=tipo).aggregate(total=Sum("valor"))["total"]
            or 0
        )

    return MetricasComedores(
        cantidad_espacios=Comedor.objects.count(),
        presupuesto_desayuno=_presupuesto("desayuno"),
        presupuesto_merienda=_presupuesto("merienda"),
        presupuesto_comida=_presupuesto("comida"),
    )


def registrar_observador_dashboard(callback: Callable[[], None]) -> None:
    """Registra un observador sin exponer los modelos o señales del dominio."""

    def _notificar(**_kwargs):
        callback()

    uid_base = f"comedores.dashboard.{callback.__module__}.{callback.__name__}"
    for signal, sender, suffix in (
        (post_save, Comedor, "save-comedor"),
        (post_delete, Comedor, "delete-comedor"),
        (post_soft_delete, Comedor, "soft-delete-comedor"),
        (post_restore, Comedor, "restore-comedor"),
        (post_save, ValorComida, "save-valor-comida"),
        (post_delete, ValorComida, "delete-valor-comida"),
    ):
        signal.connect(
            _notificar,
            sender=sender,
            dispatch_uid=f"{uid_base}.{suffix}",
        )


def obtener_ids_comedores() -> tuple[int, ...]:
    """Expone los identificadores de todos los comedores para adaptadores externos."""

    return tuple(Comedor.objects.values_list("pk", flat=True))


def obtener_ids_comedores_del_tecnico(user) -> tuple[int, ...]:
    """Expone los comedores asignados a las dúplas activas de un técnico."""

    duplas = user.dupla_tecnico.filter(estado="Activo")
    return tuple(Comedor.objects.filter(dupla__in=duplas).values_list("pk", flat=True))


def obtener_ids_organizaciones_de_comedores(
    comedor_ids: tuple[int, ...]
) -> tuple[int, ...]:
    """Expone las organizaciones vinculadas a una selección de comedores."""

    return tuple(
        Comedor.objects.filter(pk__in=comedor_ids, organizacion__isnull=False)
        .values_list("organizacion_id", flat=True)
        .distinct()
    )


def obtener_ids_organizaciones() -> tuple[int, ...]:
    """Expone los identificadores de todas las organizaciones."""

    return tuple(Organizacion.objects.values_list("pk", flat=True))


# ---------------------------------------------------------------------------
# Selector de destinatarios de comunicados (issue #2505)
#
# Comunicados necesita buscar comedores y organizaciones con los mismos filtros
# combinables de sus listados. El contrato `comedores-core-public-boundary` le
# prohibe importar `comedores.models`, `comedores.services` y
# `organizaciones.models`, asi que la busqueda vive aca y devuelve DTOs: del
# otro lado del limite no circula ningun objeto del ORM.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DestinatarioDisponible:
    """Un destinatario elegible, tal como lo muestra el panel."""

    id: int
    nombre: str
    detalle: str = ""


@dataclass(frozen=True)
class PaginaDestinatarios:
    """Una pagina de resultados con lo necesario para paginar en el cliente."""

    items: tuple[DestinatarioDisponible, ...]
    total: int
    hay_mas: bool


def _detalle(*partes) -> str:
    return " · ".join(str(parte) for parte in partes if parte)


def _acotar(queryset, ids_scope):
    """Aplica el alcance del usuario.

    ``ids_scope`` en ``None`` significa alcance total: no se materializa la
    lista de ids para evitar un ``IN`` con decenas de miles de elementos.
    """

    if ids_scope is None:
        return queryset
    return queryset.filter(pk__in=tuple(ids_scope))


def _pagina(queryset, page: int, page_size: int, a_dto) -> PaginaDestinatarios:
    page = max(1, page)
    page_size = max(1, page_size)
    total = queryset.count()
    inicio = (page - 1) * page_size
    fin = inicio + page_size
    return PaginaDestinatarios(
        items=tuple(a_dto(fila) for fila in queryset[inicio:fin]),
        total=total,
        hay_mas=fin < total,
    )


def buscar_comedores_para_destinatarios(
    request_or_get,
    *,
    ids_scope=None,
    page: int = 1,
    page_size: int = 25,
) -> PaginaDestinatarios:
    """Comedores del alcance dado que matchean los filtros combinables."""

    from comedores.services.comedor_service.impl import (  # pylint: disable=import-outside-toplevel
        COMEDOR_ADVANCED_FILTER,
    )

    queryset = (
        _acotar(Comedor.objects.all(), ids_scope)
        .select_related("provincia", "municipio", "localidad", "programa")
        .order_by("nombre", "id")
    )
    queryset = COMEDOR_ADVANCED_FILTER.filter_queryset(queryset, request_or_get)
    return _pagina(
        queryset.distinct(),
        page,
        page_size,
        lambda comedor: DestinatarioDisponible(
            id=comedor.pk,
            nombre=comedor.nombre or f"Comedor {comedor.pk}",
            detalle=_detalle(
                getattr(comedor.provincia, "nombre", None),
                getattr(comedor.municipio, "nombre", None),
                getattr(comedor.localidad, "nombre", None),
            ),
        ),
    )


def buscar_organizaciones_para_destinatarios(
    request_or_get,
    *,
    ids_scope=None,
    page: int = 1,
    page_size: int = 25,
) -> PaginaDestinatarios:
    """Organizaciones del alcance dado que matchean los filtros combinables."""

    from organizaciones.filter_config import (  # pylint: disable=import-outside-toplevel
        ORGANIZACION_ADVANCED_FILTER,
    )

    queryset = (
        _acotar(Organizacion.objects.all(), ids_scope)
        .select_related("tipo_entidad", "provincia", "municipio", "localidad")
        .order_by("nombre", "id")
    )
    queryset = ORGANIZACION_ADVANCED_FILTER.filter_queryset(queryset, request_or_get)
    return _pagina(
        queryset.distinct(),
        page,
        page_size,
        lambda organizacion: DestinatarioDisponible(
            id=organizacion.pk,
            nombre=organizacion.nombre or f"Organizacion {organizacion.pk}",
            detalle=_detalle(
                getattr(organizacion.tipo_entidad, "nombre", None),
                getattr(organizacion.provincia, "nombre", None),
                getattr(organizacion.municipio, "nombre", None),
            ),
        ),
    )


def _nombres(queryset, ids, ids_scope) -> tuple[DestinatarioDisponible, ...]:
    if not ids:
        return ()
    filas = _acotar(queryset, ids_scope).filter(pk__in=tuple(ids))
    return tuple(
        DestinatarioDisponible(id=pk, nombre=nombre or f"#{pk}")
        for pk, nombre in filas.values_list("pk", "nombre")
    )


def nombres_de_comedores(ids, *, ids_scope=None) -> tuple[DestinatarioDisponible, ...]:
    """Nombres de los comedores ya elegidos, acotados al alcance del usuario."""

    return _nombres(Comedor.objects.all(), ids, ids_scope)


def nombres_de_organizaciones(
    ids, *, ids_scope=None
) -> tuple[DestinatarioDisponible, ...]:
    """Nombres de las organizaciones ya elegidas, acotadas al alcance."""

    return _nombres(Organizacion.objects.all(), ids, ids_scope)


def get_filtros_destinatarios_config() -> dict:
    """Config de filtros de ambos universos, para el panel de destinatarios."""

    from comedores.services.filter_config.impl import (  # pylint: disable=import-outside-toplevel
        get_filters_ui_config as get_comedores_filters_ui_config,
    )
    from organizaciones.filter_config import (  # pylint: disable=import-outside-toplevel
        get_filters_ui_config as get_organizaciones_filters_ui_config,
    )

    return {
        "comedores": get_comedores_filters_ui_config(),
        "organizaciones": get_organizaciones_filters_ui_config(),
    }
