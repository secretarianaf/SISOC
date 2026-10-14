"""Roles de Inspecciones escolares (PWA Sisoc Inspecciones).

El acceso lo da ``Profile.es_inspector_escolar`` y lo que puede hacer el
usuario lo decide ``Profile.inspecciones_rol``: el inspector ve y modifica lo
propio; coordinación ve todo (la administración del programa es una función de
coordinación). Igual que en DataCalle, el flag solo no alcanza: sin un rol
válido el usuario no entra a la app.
"""

from users.profile_utils import get_profile_or_none

ROL_INSPECTOR = "inspector"
ROL_COORDINACION = "coordinacion"
ROLES_INSPECCIONES = frozenset({ROL_INSPECTOR, ROL_COORDINACION})


def get_inspecciones_rol(user) -> str:
    """Rol en Inspecciones escolares, o ``""`` si no pertenece al programa."""
    if not user or not getattr(user, "is_authenticated", False):
        return ""
    if not getattr(user, "is_active", False):
        return ""
    profile = get_profile_or_none(user)
    if not getattr(profile, "es_inspector_escolar", False):
        return ""
    rol = getattr(profile, "inspecciones_rol", "") or ""
    return rol if rol in ROLES_INSPECCIONES else ""


def tiene_acceso_inspecciones(user) -> bool:
    """Si el usuario entra a la PWA y a la API de inspecciones."""
    return bool(get_inspecciones_rol(user))


def es_coordinacion_inspecciones(user) -> bool:
    """Coordinación: consulta todas las actas, borradores y evidencias."""
    return get_inspecciones_rol(user) == ROL_COORDINACION


def es_inspector_solo_app(user) -> bool:
    """El inspector es usuario de la app: se crea sin acceso SISOC web."""
    return get_inspecciones_rol(user) == ROL_INSPECTOR
