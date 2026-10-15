from rest_framework.permissions import BasePermission

from users.services_inspecciones import tiene_acceso_inspecciones


class TieneAccesoInspecciones(BasePermission):
    """Sólo usuarios del programa (flag + rol) usan la API de inspecciones.

    Qué ve cada rol lo decide ``inspecciones.services.acceso``: el inspector,
    lo propio; coordinación, todo.
    """

    message = "Este usuario no pertenece a Inspecciones escolares."

    def has_permission(self, request, view):
        return tiene_acceso_inspecciones(request.user)
