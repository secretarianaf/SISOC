"""Web API (G1 v1) of the Tablero tab (IN03): shell, live data, CSV and acta download.

``GET /api/web/inspecciones/tablero/`` runs ``TableroView`` itself and projects
its context (breadcrumb, validated filters, options, interval). The three other
routes run the native views' ``get()`` and return their response untouched, so
the figures, the CSV and the PDF/ZIP cannot drift from the HTML page and every
consumer reads the same ``inspecciones.services.tablero`` result:

- ``tablero/datos/``: the polled JSON (``no-store``), GET only;
- ``tablero/exportar.csv``: the CSV of the applied filters, GET only;
- ``tablero/descargar-actas/``: one acta as PDF or several as ZIP (``private,
  no-store``, ``nosniff``). When there is nothing to download the native view
  queues its warning and redirects to the tablero with the filters: it is never
  an empty file nor a download that looks successful.

Access: ``WebGatePermission`` and then the native ``puede_gestionar``.
"""

from django.urls import reverse
from rest_framework.response import Response

from inspecciones.views_tablero import (
    INTERVALO_MS,
    TableroDatosView,
    TableroDescargarActasView,
    TableroExportarView,
    TableroView,
)
from inspecciones.web_api import _layout, _pestanas, _WebView
from inspecciones.web_api_acta import pending_messages
from inspecciones.web_api_escuelas import _native

FILTROS = ("fecha", "provincia", "localidad", "inspector", "turno", "notificacion")


class TableroWebView(_WebView):
    """``GET /api/web/inspecciones/tablero/``: the Tablero shell and its filters."""

    http_method_names = ["get", "head"]

    def get(self, request):
        django_request = request._request  # pylint: disable=protected-access
        vista = _native(django_request, TableroView)
        context = vista.get_context_data()
        context["request"] = request
        filtros = context["filtros"].como_querystring()
        return Response(
            {
                "layout": _layout(context),
                "tabs": _pestanas(),
                "filters": {clave: str(filtros[clave]) for clave in FILTROS},
                "options": context["opciones"],
                "intervalo_ms": INTERVALO_MS,
                "urls": {
                    "datos": reverse("inspecciones_web_tablero_datos"),
                    "exportar": reverse("inspecciones_web_tablero_exportar"),
                    "descargar": reverse("inspecciones_web_tablero_descargar"),
                },
                "messages": pending_messages(request),
            }
        )


class _NativeGet(_WebView):
    """GET only: the native view's own response, unchanged."""

    http_method_names = ["get"]
    view_class = TableroDatosView

    def get(self, request):
        django_request = request._request  # pylint: disable=protected-access
        return self.view_class().get(django_request)


class TableroDatosWebView(_NativeGet):
    """``GET /api/web/inspecciones/tablero/datos/`` (``TableroDatosView``)."""

    view_class = TableroDatosView


class TableroExportarWebView(_NativeGet):
    """``GET /api/web/inspecciones/tablero/exportar.csv`` (``TableroExportarView``)."""

    view_class = TableroExportarView


class TableroDescargarWebView(_NativeGet):
    """``GET /api/web/inspecciones/tablero/descargar-actas/``."""

    view_class = TableroDescargarActasView
