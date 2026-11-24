"""Web API (G1 v1) of the CDI nomina attendance screen (``nomina_asistencia.html``) for React.

Session transport over the native view: ``AsistenciaNominaCentroView`` itself runs the
scoped centre (404 outside the actor's scope), the date parsing and its error message,
the rows (active nomina plus historical attendance), the counters and the POST
(``AsistenciaNominaCentroInfanciaService.guardar``, its validation message, the success
message and the redirect). Order of checks:

1. G1 (``WebGatePermission``): 401/403 JSON, or the signed attestation.
2. The same permission code as the URL decorator in ``centrodeinfancia/urls.py``
   (``change_centrodeinfancia``).
3. The native dispatch.

GET answers the data the template draws. The POST accepts urlencoded only (the native
form); a native redirect becomes ``{"ok": true, "redirect": <Location>}`` and the queued
message shows on the destination page, as with the HTML. The month calendar the page
opens stays the native JSON endpoint (``.../asistencia/calendario/``), which the screen calls
as the native script does. Responses are ``private, no-store``.
"""

from django.http import JsonResponse
from django.utils import dateformat
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie

from centrodeinfancia.views import AsistenciaNominaCentroView
from centrodeinfancia.web_api import pending_messages
from centrodeinfancia.web_api_observaciones import _ObservacionTransportMixin

PERMISO_ASISTENCIA = "centrodeinfancia.change_centrodeinfancia"


@method_decorator(ensure_csrf_cookie, name="dispatch")
@method_decorator(csrf_protect, name="dispatch")
class AsistenciaWebView(_ObservacionTransportMixin, AsistenciaNominaCentroView):
    """``/api/web/cdi/centros/<pk>/nomina/asistencia/``: native attendance screen."""

    permission_code = PERMISO_ASISTENCIA

    def render_to_response(self, context, **response_kwargs):
        centro = context["centro"]
        fecha = context["fecha"]
        return JsonResponse(
            {
                "centro": {"id": centro.pk, "nombre": str(centro.nombre)},
                "fecha": fecha.isoformat(),
                "fecha_label": dateformat.format(fecha, "d/m/Y"),
                "rows": [
                    {
                        "id": fila["nomina"].pk,
                        "nombre": fila["nombre_completo"],
                        "dni": str(fila["dni"]) if fila["dni"] else "-",
                        "sala": str(fila["nomina"].sala or "-"),
                        "presente": fila["presente"],
                        "observaciones": fila["observaciones"] or "",
                    }
                    for fila in context["filas"]
                ],
                "totals": {
                    "presentes": context["total_presentes"],
                    "ausentes": context["total_ausentes"],
                    "sin_marcar": context["total_sin_marcar"],
                },
                "messages": pending_messages(self.request),
            }
        )
