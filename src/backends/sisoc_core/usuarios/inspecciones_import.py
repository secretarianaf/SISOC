"""Columnas ``DNI`` e ``Inspecciones`` del importador de usuarios.

Inspecciones escolares (PWA Sisoc Inspecciones): la columna ``Inspecciones``
asigna el rol en el programa. Como en el ABM, sólo puede asignarlo quien tiene
la sección "Inspecciones escolares": el importador sólo exige ``auth.add_user``
y coordinación ve todas las actas y evidencias. Si el actor no tiene la
sección, la fila se rechaza (no se descarta la columna en silencio).
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from users.models import Profile
from users.secciones_usuario import (
    SECCION_INSPECCIONES_ESCOLARES,
    secciones_habilitadas,
)

ROLES_IMPORTACION = {
    "inspector": Profile.InspeccionesRol.INSPECTOR,
    "inspectora": Profile.InspeccionesRol.INSPECTOR,
    "coordinacion": Profile.InspeccionesRol.COORDINACION,
    "coordinador": Profile.InspeccionesRol.COORDINACION,
    "coordinadora": Profile.InspeccionesRol.COORDINACION,
}


@dataclass(frozen=True)
class DatosInspecciones:
    """Rol y DNI validados de la fila (vacíos si no informa ``Inspecciones``)."""

    rol: str = ""
    dni: str = ""

    @property
    def es_solo_app(self) -> bool:
        """El inspector es usuario sólo de la app, como en el alta manual."""
        return self.rol == Profile.InspeccionesRol.INSPECTOR


def _normalizar(valor: str) -> str:
    texto = unicodedata.normalize("NFKD", valor.strip())
    return "".join(ch for ch in texto if not unicodedata.combining(ch)).lower()


def _resolver_rol(valor: str) -> str:
    if not valor:
        return ""
    rol = ROLES_IMPORTACION.get(_normalizar(valor))
    if rol is None:
        raise ValidationError(
            f"Rol de Inspecciones invalido: '{valor}'. "
            "Los valores validos son: inspector, coordinacion."
        )
    return rol


def resolver_inspecciones_fila(
    row_data: dict, *, email: str, actor
) -> DatosInspecciones:
    """Valida las columnas de Inspecciones de la fila (spec §3).

    DNI y correo son obligatorios; el DNI se guarda sólo con dígitos.
    """
    rol = _resolver_rol(row_data.get("inspecciones", "").strip())
    dni_raw = row_data.get("dni", "").strip()
    if not rol:
        return DatosInspecciones(dni=dni_raw)
    if SECCION_INSPECCIONES_ESCOLARES not in secciones_habilitadas(actor):
        raise ValidationError(
            "No tiene permiso para asignar roles de Inspecciones escolares."
        )
    dni = "".join(ch for ch in dni_raw if ch not in ". -")
    if not dni or not dni.isdigit():
        raise ValidationError("Inspecciones: el DNI es obligatorio y solo con digitos.")
    if not email:
        raise ValidationError("Inspecciones: el correo es obligatorio.")
    return DatosInspecciones(rol=rol, dni=dni)


def validar_unicidad_alta(datos: DatosInspecciones, *, email: str) -> None:
    """Alta nueva: DNI y correo no pueden estar en otro usuario.

    Un duplicado se rechaza con su causa: el importador nunca pisa un usuario
    existente en silencio.
    """
    if not datos.rol:
        return
    if Profile.objects.filter(dni=datos.dni).exists():
        raise ValidationError(
            f"Duplicado: el DNI {datos.dni} ya pertenece a otro usuario."
        )
    if get_user_model().objects.filter(email__iexact=email).exists():
        raise ValidationError(
            f"Duplicado: el correo {email} ya pertenece a otro usuario."
        )


def aplicar_inspecciones(profile, datos: DatosInspecciones) -> bool:
    """Marca el flag y el rol (y el DNI si faltaba). ``True`` si cambió algo."""
    if not datos.rol:
        return False
    if datos.dni and profile.dni and profile.dni != datos.dni:
        raise ValidationError(
            f"El usuario {profile.user.username} ya tiene otro DNI cargado; "
            "no se modifica desde la importacion."
        )
    campos = []
    if not profile.es_inspector_escolar or profile.inspecciones_rol != datos.rol:
        profile.es_inspector_escolar = True
        profile.inspecciones_rol = datos.rol
        campos += ["es_inspector_escolar", "inspecciones_rol"]
    if datos.dni and not profile.dni:
        profile.dni = datos.dni
        campos.append("dni")
    if campos:
        profile.save(update_fields=campos)
    return bool(campos)
