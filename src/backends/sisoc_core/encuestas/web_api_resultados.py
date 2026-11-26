"""Survey results for React (E03, G1 v1).

``GET /api/web/encuestas/<pk>/resultados/?ronda=`` runs ``EncuestaResultadosView`` (permission
``encuestas.ver_resultados``, 404 for an unknown survey) and projects the context of
``encuesta_resultados.html`` as the template prints it: dates in local time ``d/m/Y``, floats with
the Django localization and ``floatformat``. The CSV, Excel and JSON exports stay the native GET
downloads, linked from the payload. Read only.
"""

from django.template.defaultfilters import date as date_filter
from django.template.defaultfilters import floatformat
from django.urls import reverse
from django.utils.formats import localize
from django.utils.timezone import localtime
from rest_framework.response import Response

from encuestas.views import EncuestaResultadosView
from encuestas.web_transport_encuestas import EncuestaNativeWebView, pending_messages


def _fecha(value):
    """``{{ value|date:"d/m/Y" }}``: local time, empty without a value."""
    if not value:
        return ""
    if hasattr(value, "hour"):
        value = localtime(value)
    return date_filter(value, "d/m/Y")


def _opcion(opcion):
    return {
        "texto": opcion.texto,
        "cantidad": opcion.cantidad,
        "porcentaje": localize(opcion.porcentaje),
    }


def _resultado(resultado):
    numerico = resultado.promedio is not None
    return {
        "texto": resultado.texto,
        "tipo": resultado.tipo,
        "total_respuestas": resultado.total_respuestas,
        "opciones": [_opcion(opcion) for opcion in resultado.opciones],
        "opcion_lider_texto": resultado.opcion_lider_texto,
        "numerico": (
            {
                "promedio": floatformat(resultado.promedio, 1),
                "minimo": floatformat(resultado.minimo, 0),
                "maximo": floatformat(resultado.maximo, 0),
                "posicion": localize(resultado.posicion_promedio),
            }
            if numerico
            else None
        ),
        "respuestas_texto": list(resultado.respuestas_texto),
    }


def _puntaje(puntaje):
    return {
        "usuario": puntaje.usuario or "",
        "obtenido": puntaje.obtenido,
        "total_posible": puntaje.total_posible,
        "porcentaje": localize(puntaje.porcentaje),
    }


def proyectar_resultados(context, request):
    """Context of ``encuesta_resultados.html`` as the template prints it."""
    encuesta = context["encuesta"]
    actual = context["ronda_actual"]
    return {
        "id": encuesta.pk,
        "titulo": encuesta.titulo,
        "rondas": [
            {
                "id": ronda.pk,
                "selected": actual is not None and actual.pk == ronda.pk,
                "label": (
                    f"Ronda {ronda.numero_ronda} — {ronda.get_estado_display()} "
                    f"({_fecha(ronda.fecha_apertura)})"
                ),
            }
            for ronda in context["rondas"]
        ],
        "ronda_actual": (
            {
                "id": actual.pk,
                "respuestas": actual.respuestas.count(),
                "abierta": actual.estado == "abierta",
                "estado_label": actual.get_estado_display(),
                "cierre": _fecha(actual.fecha_cierre_programada),
                "export_url": reverse(
                    "encuestas_resultados_exportar", args=[encuesta.pk, actual.pk]
                ),
            }
            if actual is not None
            else None
        ),
        "puntajes": [_puntaje(puntaje) for puntaje in context["puntajes"]],
        "resultados": [_resultado(resultado) for resultado in context["resultados"]],
        "messages": pending_messages(request),
    }


class ResultadosWebView(EncuestaNativeWebView):
    permission_codes = ["encuestas.ver_resultados"]
    native_view = EncuestaResultadosView
    http_method_names = ["get", "head", "options"]

    def get(self, request, pk):
        response = self.run_native(request, pk=pk)
        # pylint: disable-next=protected-access
        return Response(proyectar_resultados(response.context_data, request._request))
