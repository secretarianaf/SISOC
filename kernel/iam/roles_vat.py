"""Roles de VAT que necesita conocer el kernel.

El menú lateral (lo renderizan el core y cada backend) oculta lo ajeno a VAT
para usuarios "solo VAT". La regla depende solo de permisos y del perfil,
datos del kernel, así que vive acá y no en VAT, que corre en su propio
backend. ``VAT.services.access_scope`` reexporta estas funciones.
"""

from __future__ import annotations

from typing import Any

from iam.services import user_has_permission_code

ROLE_VAT_SSE_PERMISSION = "auth.role_vat_sse"
ROLE_VAT_PROVINCIAL_PERMISSION = "auth.role_provincia_vat"
ROLE_VAT_INET_PROVINCIAL_PERMISSION = "auth.role_inet_provincia"
ROLE_REFERENTE_CENTRO_PERMISSIONS = (
    "auth.role_referentecentrovat",
    "auth.role_centroreferentevat",
)
VAT_VIEW_CENTRO_PERMISSION = "VAT.view_centro"


def _user_has_any_permission_code(user, permission_codes) -> bool:
    return any(user_has_permission_code(user, code) for code in permission_codes)


def is_vat_sse(user) -> bool:
    if not user:
        return False
    return bool(
        user.is_superuser or user_has_permission_code(user, ROLE_VAT_SSE_PERMISSION)
    )


def is_vat_referente(user) -> bool:
    if not user:
        return False
    return _user_has_any_permission_code(user, ROLE_REFERENTE_CENTRO_PERMISSIONS)


def is_vat_provincial(user) -> bool:
    if not user:
        return False
    profile = getattr(user, "profile", None)
    if not getattr(profile, "es_usuario_provincial", False):
        return False
    return _user_has_any_permission_code(
        user,
        (
            ROLE_VAT_PROVINCIAL_PERMISSION,
            ROLE_VAT_INET_PROVINCIAL_PERMISSION,
            VAT_VIEW_CENTRO_PERMISSION,
        ),
    )


def es_usuario_solo_vat(user: Any) -> bool:
    if not user or not user.is_authenticated or user.is_superuser:
        return False
    return bool(is_vat_sse(user) or is_vat_referente(user) or is_vat_provincial(user))
