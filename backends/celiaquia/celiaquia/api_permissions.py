"""Acceso a la API de Celiaquia por modulo.

Las pantallas Django se protegen en `celiaquia/urls.py` y `global_urls.py` con
`permissions_any_required`. Sin un equivalente aca, cualquier usuario logueado
de SISOC alcanzaba la API: un perfil `es_usuario_provincial` de otro programa
(CDI, VAT) cuenta como provincia en `scope.is_provincial`.

Estas clases solo responden "puede entrar a esta parte del modulo". Que puede
hacer cada rol adentro lo siguen decidiendo las acciones de `api_views.py`.
"""

from rest_framework.permissions import BasePermission

from iam.services import user_has_permission_code


class _PermisoDeModulo(BasePermission):
    """Misma regla que `permissions_any_required`: superuser o el permiso."""

    permiso = ""

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            return False
        return user.is_superuser or user_has_permission_code(user, self.permiso)


class TieneAccesoExpedientes(_PermisoDeModulo):
    """Expedientes, legajos y catalogos: lo que exige `expediente_list`."""

    message = "Este usuario no tiene habilitado Celiaquía."
    permiso = "celiaquia.view_expediente"


class TieneAccesoCupos(_PermisoDeModulo):
    """Cupos, movimientos y pagos: lo que exige `cupo_dashboard`.

    Los pagos se alcanzan desde el detalle de cupo de la provincia, asi que
    comparten permiso.
    """

    message = "Este usuario no tiene habilitado el dashboard de cupos."
    permiso = "celiaquia.view_cupo_dashboard"


class TieneAccesoReporte(_PermisoDeModulo):
    """Reporte por provincias: lo que exige `reporter_provincias`."""

    message = "Este usuario no tiene habilitado el reporte de Celiaquía."
    permiso = "celiaquia.view_reporte_provincias"
