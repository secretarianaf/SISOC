"""Web API (G1 v1) of the CDF attendance sheet (CDF-D).

Same access chain as ``centrodefamilia.web_api``: G1 session and web
prerequisites, then ``centrodefamilia.view_centro``. After that the native
``AsistenciaActividadView.dispatch`` runs unchanged: a missing activity is 404
and an actor who may not take attendance (``puede_tomar_asistencia_cdf``: the
centre referente, an active ``AccesoCDF``, the SSE role or a superuser) is 403.

- GET runs the native ``get_context_data``: the date (today by default, an
  invalid or future date falls back to today with its warning) and the sheet of
  the currently enrolled participants only.
- POST runs the native ``post()``: ``AsistenciaActividadService.registrar`` in
  one transaction (an unmarked participant is saved as absent, the sheet is
  ``update_or_create`` per participant and date) and its redirect, answered as
  JSON (``url`` plus the queued message, which stays queued for the native
  page). An invalid date saves nothing and the redirect carries the error.

Nothing is retried: a repeated POST is a new native request.
"""

from django.urls import reverse
from rest_framework.response import Response

from centrodefamilia.views.asistencia import AsistenciaActividadView
from centrodefamilia.web_api import CdfWebView, native_view, pending_messages, rendered
from centrodefamilia.web_api_actividades import peek_messages


def _planilla(context):
    fecha = context["fecha"]
    actividad = context["actividad"]
    centro = context["centro"]
    return {
        "actividad": {
            "id": actividad.pk,
            "nombre": actividad.actividad.nombre,
            "categoria": actividad.actividad.categoria.nombre,
            "estado_display": str(actividad.get_estado_display()),
            "horariosdesde": rendered(actividad.horariosdesde),
            "horarioshasta": rendered(actividad.horarioshasta),
        },
        "centro": {"id": centro.pk, "nombre": centro.nombre},
        "fecha": fecha.strftime("%Y-%m-%d"),
        "fecha_display": fecha.strftime("%d/%m/%Y"),
        "fecha_error": context["fecha_error"],
        "ya_tomada": bool(context["ya_tomada"]),
        "totales": {
            "presentes": context["total_presentes"],
            "ausentes": context["total_ausentes"],
            "sin_marcar": context["total_sin_marcar"],
        },
        "filas": [
            {
                "id": fila["participante"].pk,
                "apellido": fila["participante"].ciudadano.apellido,
                "nombre": fila["participante"].ciudadano.nombre,
                "documento": rendered(fila["participante"].ciudadano.documento),
                "presente": fila["presente"],
            }
            for fila in context["filas"]
        ],
        "urls": {
            "centro_list": reverse("centro_list"),
            "centro_detail": reverse("centro_detail", args=[centro.pk]),
            "detalle": context["detalle_url"],
        },
    }


class AsistenciaWebView(CdfWebView):
    """``/api/web/cdf/actividades/<pk>/asistencia/``: the sheet of a date or the native save."""

    http_method_names = ["get", "post"]

    def get(self, request, pk):
        vista = native_view(AsistenciaActividadView, request, pk=pk)
        django_request = request._request  # pylint: disable=protected-access
        respuesta = vista.dispatch(django_request, pk=pk)
        payload = _planilla(respuesta.context_data)
        payload["messages"] = pending_messages(request)
        return Response(payload)

    def post(self, request, pk):
        vista = native_view(AsistenciaActividadView, request, pk=pk)
        django_request = request._request  # pylint: disable=protected-access
        respuesta = vista.dispatch(django_request, pk=pk)
        queued = peek_messages(request)
        return Response(
            {
                "url": respuesta["Location"],
                "message": queued[-1]["message"] if queued else "",
                "level": queued[-1]["level"] if queued else "info",
            }
        )
