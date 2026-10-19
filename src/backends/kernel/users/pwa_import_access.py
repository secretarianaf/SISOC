"""Resolución de espacios de Comedores requerida por importaciones PWA."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class ComedorOrganizacionPWA:
    """Comedor expandido desde una organización asignada en un import PWA."""

    comedor_id: int
    organizacion_id: int


@dataclass(frozen=True)
class SeleccionAccesosPWAImportacion:
    """IDs y expansiones de dominio necesarios para sincronizar accesos PWA."""

    organizacion_ids: tuple[int, ...] = ()
    comedor_ids: tuple[int, ...] = ()
    comedores_por_organizacion: tuple[ComedorOrganizacionPWA, ...] = ()
    comedor_id_alimentar_comunidad: int | None = None

    @property
    def tiene_asignaciones(self) -> bool:
        return bool(self.organizacion_ids or self.comedor_ids)


ResolverAccesosPWAImportacion = Callable[[str, str], SeleccionAccesosPWAImportacion]
_resolver: ResolverAccesosPWAImportacion | None = None


def registrar_resolvedor_accesos_pwa_importacion(
    resolver: ResolverAccesosPWAImportacion,
) -> None:
    """Registra el proveedor de Comedores para importaciones PWA de Users."""
    global _resolver  # pylint: disable=global-statement

    if _resolver is None or _resolver is resolver:
        _resolver = resolver
        return
    raise ValueError("Ya existe un resolvedor de accesos PWA de importacion.")


def resolver_accesos_pwa_importacion(
    organizaciones_raw: str, comedores_raw: str
) -> SeleccionAccesosPWAImportacion:
    """Valida y expande las asignaciones de Comedores de una fila PWA."""
    if _adaptador is None and not organizaciones_raw and not comedores_raw:
        return SeleccionAccesosPWAImportacion()
    if _resolver is None:
        raise RuntimeError(
            "No hay un resolvedor de accesos PWA de importacion registrado."
        )
    return _resolver(organizaciones_raw, comedores_raw)


@dataclass(frozen=True)
class AdaptadorImportacionPWA:
    """Funciones del dueño ejecutadas en la transacción local del worker."""

    resolver: ResolverAccesosPWAImportacion
    construir_especificaciones: Callable[[SeleccionAccesosPWAImportacion], list[dict]]
    permisos_asignables: Callable
    sincronizar: Callable


_adaptador: AdaptadorImportacionPWA | None = None


def registrar_adaptador_importacion_pwa(adaptador: AdaptadorImportacionPWA) -> None:
    """Registro idempotente de ready(); no contiene transporte HTTP."""
    global _adaptador  # pylint: disable=global-statement
    if _adaptador is not None and _adaptador is not adaptador:
        raise ValueError("Ya existe un adaptador PWA de importacion.")
    registrar_resolvedor_accesos_pwa_importacion(adaptador.resolver)
    _adaptador = adaptador


def construir_especificaciones_accesos(seleccion):
    """El dueño conserva las constantes y precedencias de la asociación."""
    if _adaptador is None:
        if seleccion.tiene_asignaciones:
            _no_disponible()
        return []
    return _adaptador.construir_especificaciones(seleccion)


def get_assignable_pwa_permission_codes(actor, comedor_id=None):
    """Sin proveedor no se conceden ni se revocan permisos de Espacios."""
    if _adaptador is None:
        return []
    return _adaptador.permisos_asignables(actor, comedor_id)


def sync_representante_accesses(*, user, access_specs, actor):
    """Debe invocarse dentro del atomic de usuario y checkpoint del worker."""
    if _adaptador is None:
        _no_disponible()
    return _adaptador.sincronizar(user=user, access_specs=access_specs, actor=actor)


def _no_disponible():
    from django.core.exceptions import (
        ValidationError,
    )  # pylint: disable=import-outside-toplevel

    raise ValidationError(
        "Espacios comunitarios no está disponible para esta fila de importacion. "
        "No se modificaron el usuario ni sus accesos."
    )


def validar_fila_sin_adaptador(row_data, *, is_pwa_import, user):
    """Rechaza efectos dependientes ANTES de escribir, sin ORM de negocio.

    Reutiliza el clasificador C1 para grupos/permisos, también para bajas que
    resulten de reemplazar. No interpretar falta del proveedor como permiso.
    """
    if _adaptador is not None:
        return
    from django.contrib.auth.models import (
        Group,
    )  # pylint: disable=import-outside-toplevel
    from users.admin_operations import (
        operacion_requiere_espacios,
    )  # pylint: disable=import-outside-toplevel

    if any(
        str(row_data.get(field, "")).strip()
        for field in ("organizaciones", "comedores")
    ):
        _no_disponible()
    if is_pwa_import and not row_data.get("inspecciones", "").strip():
        _no_disponible()
    tokens = [
        token.strip()
        for token in row_data.get("permisos", "").split(";")
        if token.strip()
    ]
    grupos = list(Group.objects.filter(name__in=tokens))
    if set(tokens) - {grupo.name for grupo in grupos}:
        _no_disponible()
    data = {"groups": [grupo.pk for grupo in grupos]}
    if (
        user is not None
        and row_data.get("accion_grupos", "").strip().lower() == "reemplazar"
    ):
        data["groups"] += list(user.groups.values_list("pk", flat=True))
        data["user_permissions"] = list(
            user.user_permissions.values_list("pk", flat=True)
        )
    if operacion_requiere_espacios(data):
        _no_disponible()
