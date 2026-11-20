"""Web API (G1 v1) of the monthly benefits certifications history (CO05.01).

``GET /api/web/comedores/comedores/<pk>/certificaciones-prestaciones/``.

In a split deploy the core checks the session and the web prerequisites and
signs each request; the runtime only serves requests its ``WebGateMiddleware``
verified. In the monolith ``WebGatePermission`` evaluates the same policy
locally. After that the native route guard applies unchanged (superuser bypass
included): ``certificaciones_prestaciones_historial`` is
``permissions_any_required(["comedores.view_comedor", "admisiones.view_admision"])``.

The endpoint runs the native ``CertificacionesPrestacionesHistorialView`` itself
(``setup()``, ``get_queryset()`` and ``get_context_data()``: comedor scope,
filters, ordering, 20 per page, invalid page 404) and renders every text with the
expression of ``certificaciones_prestaciones_historial.html``. It only reads: the
certification is produced by the PWA, and the PDF stays a native binary download
(``descargar_certificacion_prestaciones_web``), never moved to the client.
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
from comedores.views.comedor import CertificacionesPrestacionesHistorialView
from comedores.web_api_comedores import pending_messages
from comedores.web_api_montos import _pagina

VER_CERTIFICACIONES = ["comedores.view_comedor", "admisiones.view_admision"]

_TEMPLATES = {}

# Expressions of ``certificaciones_prestaciones_historial.html``.
_FILA = {
    "periodo": '{{ c.periodo|date:"m/Y" }}',
    "usuario": "{{ c.usuario.get_full_name|default:c.usuario.username }}",
    "creado": '{{ c.creado|date:"d/m/Y H:i" }}',
}
_GENERADOR = (
    "{% if item.usuario__first_name or item.usuario__last_name %}"
    "{{ item.usuario__first_name }} {{ item.usuario__last_name }}"
    "{% else %}{{ item.usuario__username }}{% endif %}"
)


class VerCertificaciones(BasePermission):
    """Same rule as the native ``permissions_any_required`` of the route."""

    def has_permission(self, request, view):
        return _has_any_permissions(request.user, VER_CERTIFICACIONES)


def _render(expression, context):
    if expression not in _TEMPLATES:
        _TEMPLATES[expression] = Template(expression)
    return unescape(_TEMPLATES[expression].render(context)).strip()


def _fila(certificacion, comedor_id):
    context = Context({"c": certificacion})
    return {
        "id": certificacion.pk,
        "periodo": _render(_FILA["periodo"], context),
        # ``{% if certificacion.usuario %}`` else a dash.
        "usuario": (
            _render(_FILA["usuario"], context) if certificacion.usuario else "-"
        ),
        "conforme": bool(certificacion.conforme),
        "creado": _render(_FILA["creado"], context),
        "pdf_url": (
            reverse(
                "descargar_certificacion_prestaciones_web",
                args=[comedor_id, certificacion.pk],
            )
            if certificacion.certificacion_pdf
            else None
        ),
    }


def _generador(item):
    texto = _render(_GENERADOR, Context({"item": item}))
    return {"id": item["usuario_id"], "label": " ".join(texto.split())}


class CertificacionesHistorialWebView(APIView):
    """Read-only projection of ``CertificacionesPrestacionesHistorialView``."""

    authentication_classes = [SessionAuthentication]
    permission_classes = [WebGatePermission, VerCertificaciones]
    renderer_classes = [JSONRenderer]
    http_method_names = ["get", "head"]

    def get(self, request, pk):
        django_request = request._request  # pylint: disable=protected-access
        vista = CertificacionesPrestacionesHistorialView()
        vista.setup(django_request, pk=pk)
        try:
            vista.object_list = vista.get_queryset()
            context = vista.get_context_data()
        except Http404 as exc:
            raise NotFound() from exc
        comedor = context["comedor"]
        return Response(
            {
                "comedor": {"id": comedor.pk, "nombre": str(comedor.nombre)},
                "filtros": context["filtros"],
                "generadores": [_generador(i) for i in context["usuarios_generadores"]],
                "certificaciones": [
                    _fila(c, comedor.pk)
                    for c in context["certificaciones_prestaciones"]
                ],
                "page": _pagina(context, django_request),
                "urls": {
                    "comedores": reverse("comedores"),
                    "comedor": reverse("comedor_detalle", args=[comedor.pk]),
                    "historial": reverse(
                        "certificaciones_prestaciones_historial", args=[comedor.pk]
                    ),
                },
                "messages": pending_messages(django_request),
            }
        )
