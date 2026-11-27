"""Canonical React entry for the Celiaquía Tablero screen.

The JSON projection is the native view context: the same ``construir_tablero``
payload (aggregated, no personal data) and the same ``url_expediente`` rule
(only users with ``view_expediente`` get the link template). Filters apply in
the browser over this data, as in the native page. The URL decorator
(``view_tablero_celiaquia``) authorizes before this wrapper runs.
"""

from django.core.exceptions import PermissionDenied
from django.http import HttpResponse, HttpResponseNotAllowed, JsonResponse

from core.decorators import permissions_any_required
from celiaquia.canonical_pagos import pending_messages
from celiaquia.canonical_shell import canonical_screen
from celiaquia.services.alcance_tablero import alcance_tablero
from celiaquia.views.tablero import TableroCeliaquiaView

_native_tablero = TableroCeliaquiaView.as_view()


def _projection(request, *args, **kwargs):
    response = _native_tablero(request, *args, **kwargs)
    if response.status_code != 200:
        return response
    context = response.context_data
    return JsonResponse(
        {
            "version": 1,
            "datos": context["tablero_datos"],
            "url_expediente": context["url_expediente"],
            "messages": pending_messages(request),
        }
    )


_pantalla = canonical_screen(_native_tablero, "tablero", _projection)
_pantalla_legacy = permissions_any_required(["celiaquia.view_tablero_celiaquia"])(
    _pantalla
)


def tablero(request, *args, **kwargs):
    """Autoriza también el shell React antes de entregar cualquier respuesta."""
    if request.method not in ("GET", "HEAD"):
        return HttpResponseNotAllowed(["GET", "HEAD"])
    if not request.user.is_authenticated or not request.user.is_active:
        raise PermissionDenied
    estado, provincias = alcance_tablero(request)
    if estado == "inactiva":
        return _pantalla_legacy(request, *args, **kwargs)
    if estado == "no_disponible":
        return HttpResponse("El servicio no está disponible.", status=503)
    if estado == "denegado":
        raise PermissionDenied
    request._provincias_tablero_celiaquia = (  # pylint: disable=protected-access
        list(provincias) if estado == "provincial" else None
    )
    return _pantalla(request, *args, **kwargs)
