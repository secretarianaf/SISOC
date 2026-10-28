"""Reglas de mapeo de operadores de filtros avanzados a lookups ORM."""

from __future__ import annotations

from typing import Optional

from django.db.models import Q

from core.utils import rango_del_dia_local

DATE_TRANSFORM = "__date"


def resolve_lookup(
    field_type: str, op: str, mapped_field: str
) -> tuple[Optional[str], bool]:
    """Resuelve lookup de Django y si debe negarse el ``Q`` resultante."""

    lookup = None
    negate = False

    if field_type == "text":
        if op == "eq":
            lookup = f"{mapped_field}__iexact"
        elif op == "ne":
            lookup = f"{mapped_field}__iexact"
            negate = True
        elif op == "contains":
            lookup = f"{mapped_field}__icontains"
        elif op == "ncontains":
            lookup = f"{mapped_field}__icontains"
            negate = True
    elif field_type == "choice":
        if op == "eq":
            lookup = f"{mapped_field}__iexact"
        elif op == "ne":
            lookup = f"{mapped_field}__iexact"
            negate = True
    elif field_type == "number":
        if op == "eq":
            lookup = f"{mapped_field}__exact"
        elif op == "ne":
            lookup = f"{mapped_field}__exact"
            negate = True
        elif op == "gt":
            lookup = f"{mapped_field}__gt"
        elif op == "lt":
            lookup = f"{mapped_field}__lt"
    elif field_type == "date":
        if op == "eq":
            lookup = f"{mapped_field}__exact"
        elif op == "ne":
            lookup = f"{mapped_field}__exact"
            negate = True
        elif op == "gt":
            lookup = f"{mapped_field}__gt"
        elif op == "lt":
            lookup = f"{mapped_field}__lt"
        elif op == "gte":
            lookup = f"{mapped_field}__gte"
        elif op == "lte":
            lookup = f"{mapped_field}__lte"
    elif field_type == "boolean":
        if op == "eq":
            lookup = f"{mapped_field}__exact"
        elif op == "ne":
            lookup = f"{mapped_field}__exact"
            negate = True

    return lookup, negate


def split_date_transform(mapped_field: str) -> tuple[str, bool]:
    """Separa ``campo__date`` en ``campo`` e indica si traía la transformación."""

    if mapped_field.endswith(DATE_TRANSFORM):
        return mapped_field[: -len(DATE_TRANSFORM)], True
    return mapped_field, False


def build_local_day_q(base_field: str, op: str, fecha) -> Optional[Q]:
    """Compara un ``DateTimeField`` contra un día local con rangos explícitos.

    Reemplaza ``campo__date__<op>``, que depende de las tablas de zonas
    horarias de MySQL (ver ``core.utils.rango_del_dia_local``).
    """

    inicio, fin = rango_del_dia_local(fecha)
    del_dia = Q(**{f"{base_field}__gte": inicio, f"{base_field}__lt": fin})
    return {
        "eq": del_dia,
        "ne": ~del_dia,
        "gt": Q(**{f"{base_field}__gte": fin}),
        "lt": Q(**{f"{base_field}__lt": inicio}),
        "gte": Q(**{f"{base_field}__gte": inicio}),
        "lte": Q(**{f"{base_field}__lt": fin}),
    }.get(op)
