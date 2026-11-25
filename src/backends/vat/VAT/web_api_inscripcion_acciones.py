"""Web API (G1 v1) de las acciones de inscripción de VAT (V03.02, U3).

Cambio de estado (oferta y curso), cambio de estado en lote y alta rápida desde el detalle
de comisión: cada endpoint ejecuta el ``post`` de la vista nativa, de modo que el alcance
por centro, el servicio ``InscripcionService`` y los mensajes son los nativos. Los POST con
redirección responden ``{"ok": true, "redirect": <url>}`` (el mensaje queda encolado para la
página de destino, como en la vista nativa); los que ya son JSON conservan su cuerpo y su
estado. Una inscripción o comisión fuera de alcance da 404 y no escribe nada.
"""

import json

from django.http import Http404, HttpResponseRedirect
from rest_framework.exceptions import NotFound
from rest_framework.response import Response

from VAT.views.curso import (
    InscripcionCursoCambiarEstadoLoteView,
    InscripcionCursoCambiarEstadoView,
    InscripcionRapidaComisionCursoView,
)
from VAT.views.oferta_institucional import InscripcionCambiarEstadoView
from VAT.views.persona import InscripcionRapidaComisionView
from VAT.web_api_common import VatNativeReadView


class _AccionWebView(VatNativeReadView):
    """POST que ejecuta el ``post`` de la vista nativa."""

    http_method_names = ["post"]

    def post(self, request, **kwargs):
        vista = self.native(**kwargs)
        try:
            respuesta = vista.post(vista.request, **kwargs)
        except Http404 as exc:
            raise NotFound() from exc
        if isinstance(respuesta, HttpResponseRedirect):
            return Response({"ok": True, "redirect": respuesta["Location"]})
        return Response(json.loads(respuesta.content), status=respuesta.status_code)


class InscripcionCambiarEstadoWebView(_AccionWebView):
    """``POST .../inscripciones-persona/<pk>/cambiar-estado/``."""

    native_class = InscripcionCambiarEstadoView
    codigos = ["VAT.change_inscripcion"]


class InscripcionCursoCambiarEstadoWebView(_AccionWebView):
    """``POST .../inscripciones-persona/cursos/<pk>/cambiar-estado/``."""

    native_class = InscripcionCursoCambiarEstadoView
    codigos = ["VAT.change_inscripcion"]


class InscripcionCursoCambiarEstadoLoteWebView(_AccionWebView):
    """``POST .../inscripciones-persona/cursos/comisiones/<pk>/cambiar-estado-lote/``."""

    native_class = InscripcionCursoCambiarEstadoLoteView
    codigos = ["VAT.change_inscripcion"]


class InscripcionRapidaComisionWebView(_AccionWebView):
    """``POST .../inscripciones-persona/rapida-comision/``."""

    native_class = InscripcionRapidaComisionView
    codigos = ["VAT.add_inscripcion"]


class InscripcionRapidaComisionCursoWebView(_AccionWebView):
    """``POST .../inscripciones-persona/cursos/rapida-comision/``."""

    native_class = InscripcionRapidaComisionCursoView
    codigos = ["VAT.add_inscripcion"]
