"""Quién administra el programa desde el backoffice (catálogo y asignaciones).

La regla vive en el kernel (``users.services_inspecciones``) porque también
decide el link del menú lateral, que se arma fuera de este backend.
"""

from users.services_inspecciones import puede_gestionar_inspecciones as puede_gestionar

__all__ = ["puede_gestionar"]
