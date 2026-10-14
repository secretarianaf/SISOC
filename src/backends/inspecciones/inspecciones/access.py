"""Quién administra el programa desde el backoffice (catálogo y asignaciones)."""

from users.services_inspecciones import es_coordinacion_inspecciones

PERMISO_GESTION = "inspecciones.gestionar_inspecciones"


def puede_gestionar(user):
    """Permiso explícito o rol de coordinación (la administración es su función)."""
    if not user or not user.is_authenticated:
        return False
    return user.has_perm(PERMISO_GESTION) or es_coordinacion_inspecciones(user)
