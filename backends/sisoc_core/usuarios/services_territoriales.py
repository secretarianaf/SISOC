"""Usuarios territoriales PNUD asignables a organizaciones de Abordaje Comunitario.

El rol se toma del texto libre ``Profile.rol``, que el issue #2444 normaliza a
los valores de estas constantes. La comparación no distingue mayúsculas para
tolerar cargas manuales previas a esa normalización.
"""

from functools import reduce
from operator import or_

from django.contrib.auth import get_user_model
from django.db.models import Q

ROL_TERRITORIAL_PNUD = "TERRITORIAL PNUD"
ROL_RESPONSABLE_TERRITORIAL_PNUD = "RESPONSABLE TERRITORIAL PNUD"
ROLES_TERRITORIALES_PNUD = (ROL_TERRITORIAL_PNUD, ROL_RESPONSABLE_TERRITORIAL_PNUD)


def usuarios_territoriales_pnud():
    """Usuarios activos con rol Territorial o Responsable Territorial PNUD."""
    rol_q = reduce(
        or_, (Q(profile__rol__iexact=rol) for rol in ROLES_TERRITORIALES_PNUD)
    )
    return (
        get_user_model()
        .objects.filter(rol_q, is_active=True)
        .order_by("last_name", "first_name", "username")
    )


def etiqueta_territorial(user):
    """``Apellido, Nombre (username)``; solo el username si no tiene nombre."""
    nombre = ", ".join(
        parte for parte in (user.last_name.strip(), user.first_name.strip()) if parte
    )
    return f"{nombre} ({user.username})" if nombre else user.username
