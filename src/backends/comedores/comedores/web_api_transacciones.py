"""Web API (G1 v1) of the DW transactions history of a comedor (CO07.01).

``GET /api/web/comedores/comedores/<pk>/transacciones/``.

In a split deploy the core checks the session and the web prerequisites and
signs each request; the runtime only serves requests its ``WebGateMiddleware``
verified. In the monolith ``WebGatePermission`` evaluates the same policy
locally. After that the native route guard applies unchanged (superuser bypass
included): ``comedor_transacciones_detalle`` is
``permissions_any_required(["comedores.view_comedor"])``.

The endpoint runs the native ``ComedorTransaccionesDetailView`` itself
(``setup()``, ``get_object()`` for the scoped comedor, and ``get_context_data()``,
which calls ``DWTransaccionesService.obtener_historico_completo``: parametrized
SQL against the DW view, 1000 per page). It renders every cell with the
expression of ``comedor_transacciones_detail.html``. Read only: the DW query is
the existing service, no new HTTP endpoint towards the DW, and a service failure
keeps the native behavior (empty list, same message as no data).
"""

from html import unescape

from django.http import Http404
from django.template import Context, Template
from django.urls import reverse
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import NotFound
from rest_framework.permissions import BasePermission
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.views import APIView

from core.decorators import _has_any_permissions
from core.web_gate import WebGatePermission
from comedores.views.comedor import ComedorTransaccionesDetailView
from comedores.web_api_comedores import pending_messages

VER_TRANSACCIONES = ["comedores.view_comedor"]

_TEMPLATES = {}

# Expressions of ``comedor_transacciones_detail.html``.
_CELDAS = {
    "periodo": "{{ transaccion.periodo_display }}",
    "movimientos": "{{ transaccion.cantidad_debitos }}",
    "transferido": "{{ transaccion.transferido_display }}",
    "gastado": "{{ transaccion.gastado_display }}",
    "saldo": "{{ transaccion.saldo_display }}",
}


class VerTransacciones(BasePermission):
    """Same rule as the native ``permissions_any_required`` of the route."""

    def has_permission(self, request, view):
        return _has_any_permissions(request.user, VER_TRANSACCIONES)


def _render(expression, context):
    if expression not in _TEMPLATES:
        _TEMPLATES[expression] = Template(expression)
    return unescape(_TEMPLATES[expression].render(context)).strip()


def _fila(transaccion):
    context = Context({"transaccion": transaccion})
    return {clave: _render(expr, context) for clave, expr in _CELDAS.items()}


class ComedorTransaccionesWebView(APIView):
    """Read-only projection of ``ComedorTransaccionesDetailView``."""

    authentication_classes = [SessionAuthentication]
    permission_classes = [WebGatePermission, VerTransacciones]
    renderer_classes = [JSONRenderer]
    http_method_names = ["get", "head"]

    def get(self, request, pk):
        django_request = request._request  # pylint: disable=protected-access
        vista = ComedorTransaccionesDetailView()
        vista.setup(django_request, pk=pk)
        try:
            vista.object = vista.get_object()
            context = vista.get_context_data()
        except Http404 as exc:
            raise NotFound() from exc
        comedor = context["comedor"]
        return Response(
            {
                "comedor": {"id": comedor.pk, "nombre": str(comedor.nombre)},
                "transacciones": [_fila(t) for t in context["transacciones"]],
                "urls": {
                    "comedores": reverse("comedores"),
                    "comedor": reverse("comedor_detalle", args=[comedor.pk]),
                },
                "messages": pending_messages(django_request),
            }
        )
