"""Estado operativo del CDI: Activo, Pendiente o Baja (#2945).

Pendiente y Baja sacan al CDI, sus trabajadores y su nómina de los PDF
descargables (``services_nomina_ninos_pdf``); los Excel lo informan en una
columna. Cambiar el estado no toca trabajadores, nómina, usuarios ni accesos.
El cambio queda en el audittrail del CDI.
"""

from django.core.exceptions import PermissionDenied, ValidationError

from centrodeinfancia.access import puede_cambiar_estado_cdi
from centrodeinfancia.models import CentroDeInfancia


def cambiar_estado_centro(*, actor, centro, estado):
    """Guarda ``estado`` en ``centro``; devuelve si cambió.

    El alcance territorial ya viene aplicado al buscar ``centro``.
    """
    if not puede_cambiar_estado_cdi(actor):
        raise PermissionDenied("No tenés permiso para cambiar el estado del CDI.")
    if estado not in CentroDeInfancia.Estado.values:
        raise ValidationError("El estado elegido no es válido.")
    if centro.estado == estado:
        return False
    centro.estado = estado
    centro.save(update_fields=["estado"])
    return True
