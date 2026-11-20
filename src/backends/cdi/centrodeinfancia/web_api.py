"""Web API (G1 v1) of the CDI reports screen for the React page.

``/api/web/cdi/`` is published by this backend (``url_prefixes`` in
``src/backends/config/backends.json``). In a split deploy the core checks the
session and the web prerequisites and signs each request; the runtime only
serves requests its ``WebGateMiddleware`` verified. In the monolith
``WebGatePermission`` evaluates the same policy locally. After that the
native rule applies unchanged: ``auth.role_reportes_cdi`` (or superuser), the
same check as ``permissions_any_required`` on ``centrodeinfancia_reportes``.

The summary reuses ``views_reportes.ReportesCDIView`` itself (scope, province
filter, variants and the first sheet of the workbook), so it cannot drift from
the HTML page; this module only projects that context to JSON. The XLSX stays
the native backend download (``centrodeinfancia_reportes_descargar``).
Read-only: GET only.
"""

from django.contrib import messages
from django.urls import reverse
from django.utils import formats
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import BasePermission
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.views import APIView

from centrodeinfancia.views_reportes import ReportesCDIView, puede_ver_reportes
from core.web_gate import WebGatePermission

MESSAGE_LEVELS = {
    messages.ERROR: "error",
    messages.WARNING: "warning",
    messages.SUCCESS: "success",
}


class PuedeVerReportes(BasePermission):
    """Same rule as the URL decorator: ``auth.role_reportes_cdi`` or superuser."""

    def has_permission(self, request, view):
        return puede_ver_reportes(request.user)


def pending_messages(request):
    """Messages the native page would show (and consume) with toastr."""
    return [
        {"message": str(item), "level": MESSAGE_LEVELS.get(item.level, "info")}
        for item in messages.get_messages(request)
    ]


def breadcrumb(items):
    """``components/breadcrumb.html``: only a non-last item with a URL is a link."""
    return [
        {
            "text": str(item["text"]),
            "url": (
                item.get("url")
                if item.get("url") and not item.get("active") and index < len(items) - 1
                else None
            ),
        }
        for index, item in enumerate(items)
    ]


class ReportesWebView(APIView):
    """``GET /api/web/cdi/reportes/``: selectors and the Resumen preview."""

    authentication_classes = [SessionAuthentication]
    permission_classes = [WebGatePermission, PuedeVerReportes]
    renderer_classes = [JSONRenderer]
    http_method_names = ["get", "head"]

    def get(self, request):
        django_request = request._request  # pylint: disable=protected-access
        vista = ReportesCDIView()
        vista.setup(django_request)
        context = vista.get_context_data()
        return Response(
            {
                "breadcrumb": breadcrumb(context["breadcrumb_items"]),
                "provincias": [
                    {"id": provincia.pk, "nombre": provincia.nombre}
                    for provincia in context["provincias"]
                ],
                "provincia_seleccionada": context["provincia_seleccionada"],
                "variantes": [
                    {"value": codigo, "label": str(etiqueta)}
                    for codigo, etiqueta in context["variantes"]
                ],
                "resumen": {
                    "columnas": list(context["resumen_columnas"]),
                    "filas": [
                        [str(formats.localize(celda)) for celda in fila]
                        for fila in context["resumen_filas"]
                    ],
                },
                "urls": {
                    "pantalla": reverse("centrodeinfancia_reportes"),
                    "descarga": reverse("centrodeinfancia_reportes_descargar"),
                },
                "messages": pending_messages(django_request),
            }
        )
