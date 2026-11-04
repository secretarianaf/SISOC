"""Acceso móvil confirmado por el dueño de Espacios Comunitarios."""

from rest_framework.exceptions import APIException
from rest_framework.permissions import BasePermission

from core.internal_services import pedir_json_interno


class EspaciosNoDisponible(APIException):
    status_code = 503
    default_detail = (
        "No pudimos verificar tu acceso a Espacios Comunitarios. Reintentá más tarde."
    )


class AccesoEspaciosComunitarios(BasePermission):
    message = "No tenés acceso habilitado a Espacios Comunitarios."

    def has_permission(self, request, view):
        if not request.user.is_authenticated or not request.user.is_active:
            return False
        result = pedir_json_interno(request, "pwa", "/interno/espacios/contexto/")
        data = result.data
        if (
            result.status != 200
            or not isinstance(data, dict)
            or not isinstance(data.get("pwa"), dict)
            or not isinstance(data["pwa"].get("is_pwa_user"), bool)
        ):
            raise EspaciosNoDisponible()
        return data["pwa"]["is_pwa_user"]
