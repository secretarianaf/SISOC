"""Secciones del ABM de usuarios habilitadas por permiso.

Cada sección específica de un programa (Comedores, DataCalle) o de
administración se muestra y se puede editar sólo si quien crea o edita el
usuario tiene su permiso ``auth.role_usuarios_seccion_*``. Los datos
personales, de acceso, grupos y alcance territorial son generales y no dependen
de estas secciones.

Los permisos se agrupan en grupos ("roles") para armar perfiles de gestión:
por ejemplo ``Usuarios - Gestor Comedores`` habilita las secciones de
Comedores y ``Coordinador DataCalle`` sólo la de DataCalle.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SeccionUsuario:
    clave: str
    permiso: str
    nombre: str


SECCION_MOBILE_COMEDORES = "mobile_comedores"
SECCION_TERRITORIAL_COMEDOR = "territorial_comedor"
SECCION_EQUIPOS_TECNICOS = "equipos_tecnicos"
SECCION_DATACALLE = "datacalle"
SECCION_ADMINISTRACION = "administracion"

SECCIONES_USUARIO = (
    SeccionUsuario(
        SECCION_MOBILE_COMEDORES,
        "auth.role_usuarios_seccion_mobile_comedores",
        "Usuarios - Sección Acceso SISOC Mobile (Comedores)",
    ),
    SeccionUsuario(
        SECCION_TERRITORIAL_COMEDOR,
        "auth.role_usuarios_seccion_territorial_comedor",
        "Usuarios - Sección Mobile Territorial comedor",
    ),
    SeccionUsuario(
        SECCION_EQUIPOS_TECNICOS,
        "auth.role_usuarios_seccion_equipos_tecnicos",
        "Usuarios - Sección Equipos técnicos (Comedores)",
    ),
    SeccionUsuario(
        SECCION_DATACALLE,
        "auth.role_usuarios_seccion_datacalle",
        "Usuarios - Sección Acceso SISOC Mobile DataCalle",
    ),
    SeccionUsuario(
        SECCION_ADMINISTRACION,
        "auth.role_usuarios_seccion_administracion",
        "Usuarios - Sección Administración de accesos",
    ),
)

SECCIONES_COMEDORES = (
    SECCION_MOBILE_COMEDORES,
    SECCION_TERRITORIAL_COMEDOR,
    SECCION_EQUIPOS_TECNICOS,
)

TODAS_LAS_SECCIONES = frozenset(seccion.clave for seccion in SECCIONES_USUARIO)


def permiso_de_seccion(clave: str) -> str:
    for seccion in SECCIONES_USUARIO:
        if seccion.clave == clave:
            return seccion.permiso
    raise KeyError(clave)


def secciones_habilitadas(actor) -> frozenset[str]:
    """Secciones que ``actor`` puede ver y editar en el ABM de usuarios.

    Sin actor (usos internos del formulario) y el superusuario ven todas, igual
    que el resto de las restricciones por actor del formulario.
    """
    if actor is None or getattr(actor, "is_superuser", False):
        return TODAS_LAS_SECCIONES
    return frozenset(
        seccion.clave
        for seccion in SECCIONES_USUARIO
        if actor.has_perm(seccion.permiso)
    )
