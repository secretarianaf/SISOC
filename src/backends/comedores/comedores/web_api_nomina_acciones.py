"""Web API (G1 v1) of the comedor nómina actions (CO01): state change and derivation.

``POST /api/web/comedores/comedores/nomina/<pk>/cambiar-estado/`` and
``POST /api/web/comedores/comedores/nomina/<pk>/derivar/`` call the native
``nomina_cambiar_estado`` and ``nomina_derivar`` functions unchanged (scope,
validation, domain service, status codes and messages included). In front of
them only the G1 gate, the permission of the native URL and CSRF are added:

- state change: ``permissions_any_required(["comedores.change_nomina"])``;
- derivation: ``permissions_all_required(["comedores.change_nomina",
  "comedores.add_nomina"])``.

The native edit modal is not wired (its handler is commented out in
``nomina_detail.js``) and the delete and import routes stay native.
"""

from django.core.exceptions import PermissionDenied
from django.http import Http404, JsonResponse
from django.utils.cache import patch_cache_control, patch_vary_headers
from django.views.decorators.csrf import csrf_protect
from rest_framework.exceptions import APIException

from core.decorators import permissions_all_required, permissions_any_required
from core.web_gate import WebGatePermission
from comedores.views.nomina import nomina_cambiar_estado, nomina_derivar

CAMBIAR_ESTADO = ["comedores.change_nomina"]
DERIVAR = ["comedores.change_nomina", "comedores.add_nomina"]
SIN_PERMISO = "Usted no tiene permiso para realizar esta acción."


def _private(response):
    patch_cache_control(response, private=True, no_store=True)
    patch_vary_headers(response, ("Cookie",))
    return response


def _json(body, status):
    return _private(JsonResponse(body, status=status))


def _gate(request):
    """``WebGatePermission`` for a Django view: the same 401/403 bodies as DRF."""
    try:
        WebGatePermission().has_permission(request, None)
    except APIException as exc:
        detail = exc.detail if isinstance(exc.detail, dict) else {"detail": exc.detail}
        response = _json({k: str(v) for k, v in detail.items()}, exc.status_code)
        if exc.status_code == 401:
            response["WWW-Authenticate"] = "Session"
        return response
    return None


def _run(request, pk, guard, native):
    response = _gate(request)
    if response is not None:
        return response
    try:
        response = guard(native)(request, pk=pk)
    except PermissionDenied as exc:
        return _json({"detail": str(exc) or SIN_PERMISO}, 403)
    except Http404:
        return _json({"detail": "No encontrado."}, 404)
    return _private(response)


@csrf_protect
def nomina_cambiar_estado_web(request, pk):
    """The native state change, as is."""
    return _run(
        request,
        pk,
        permissions_any_required(CAMBIAR_ESTADO),
        nomina_cambiar_estado,
    )


@csrf_protect
def nomina_derivar_web(request, pk):
    """The native derivation, as is."""
    return _run(request, pk, permissions_all_required(DERIVAR), nomina_derivar)
