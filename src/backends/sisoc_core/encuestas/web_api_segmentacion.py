"""Segmentation and survey import for React (E02, G1 v1).

``GET /api/web/encuestas/<pk>/segmentacion/`` runs ``EncuestaSegmentacionView`` and projects the
context of ``encuesta_segmentacion.html``; the POST endpoints run the native views
(``SegmentacionTipoUpdateView``, ``SegmentacionAgregarDestinatarioView``,
``SegmentacionQuitarDestinatarioView`` and ``EncuestaImportarView``), whose services, messages and
redirects are unchanged. Permissions are those of ``encuestas/urls.py``.
"""

from django.http import HttpResponseRedirect
from django.urls import reverse
from rest_framework.response import Response

from encuestas.views import (
    EncuestaImportarView,
    EncuestaSegmentacionView,
    SegmentacionAgregarDestinatarioView,
    SegmentacionQuitarDestinatarioView,
    SegmentacionTipoUpdateView,
)
from encuestas.web_transport_encuestas import EncuestaNativeWebView, pending_messages

CAMBIAR = ["encuestas.change_encuesta"]


def proyectar_segmentacion(context, request):
    """Context of ``encuesta_segmentacion.html`` as the template prints it."""
    encuesta = context["encuesta"]
    segmentacion = context["segmentacion"]
    seleccionados = context["grupos_seleccionados"]
    return {
        "id": encuesta.pk,
        "titulo": encuesta.titulo,
        "disponible_pwa": bool(encuesta.disponible_pwa),
        "tipo": segmentacion.tipo if segmentacion else "",
        "grupos": [
            {"id": grupo.pk, "name": grupo.name, "selected": grupo.pk in seleccionados}
            for grupo in context["grupos_disponibles"]
        ],
        "destinatarios": [
            {
                "id": destinatario.pk,
                "tipo_label": destinatario.get_tipo_documento_display(),
                "numero_documento": destinatario.numero_documento,
            }
            for destinatario in context["destinatarios"]
        ],
        "usuarios": [
            {
                "id": usuario.pk,
                "username": usuario.get_username(),
                "full_name": usuario.get_full_name(),
            }
            for usuario in context["usuarios_destinatarios"]
        ],
        "urls": {
            "plantilla": reverse("encuestas_segmentacion_plantilla", args=[encuesta.pk])
        },
        "messages": pending_messages(request),
    }


class SegmentacionWebView(EncuestaNativeWebView):
    permission_codes = CAMBIAR
    native_view = EncuestaSegmentacionView
    http_method_names = ["get", "head", "options"]

    def get(self, request, pk):
        response = self.run_native(request, pk=pk)
        if isinstance(response, HttpResponseRedirect):
            # An approval-pending survey only allows review: the native redirect.
            return Response({"redirect": response["Location"]})
        # pylint: disable-next=protected-access
        return Response(proyectar_segmentacion(response.context_data, request._request))


class _AccionWebView(EncuestaNativeWebView):
    http_method_names = ["post", "options"]

    def post(self, request, **kwargs):
        return self.redirect_result(request, self.run_native(request, **kwargs))


class SegmentacionTipoWebView(_AccionWebView):
    permission_codes = CAMBIAR
    native_view = SegmentacionTipoUpdateView


class SegmentacionAgregarWebView(_AccionWebView):
    permission_codes = CAMBIAR
    native_view = SegmentacionAgregarDestinatarioView


class SegmentacionQuitarWebView(_AccionWebView):
    permission_codes = CAMBIAR
    native_view = SegmentacionQuitarDestinatarioView


class EncuestaImportarWebView(_AccionWebView):
    """``?mensajes=en-cola`` leaves the flash message queued for a page the client reloads."""

    permission_codes = ["encuestas.add_encuesta"]
    native_view = EncuestaImportarView

    def post(self, request, **kwargs):
        queued = request.query_params.get("mensajes") == "en-cola"
        return self.redirect_result(
            request, self.run_native(request, **kwargs), consume=not queued
        )
