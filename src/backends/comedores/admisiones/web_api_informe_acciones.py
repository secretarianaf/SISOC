"""Web API (G1 v1) of the actions of the technical-report detail page (AD02.02).

``POST .../informes/<tipo>/<pk>/docx-editado/`` (multipart, ``docx_editado``) and
``POST .../informes/<tipo>/<pk>/revision/`` (JSON ``estado``, ``observacion``,
``campos_a_subsanar``) run the native ``InformeTecnicoDetailView`` handlers
(``_handle_subir_docx_editado_post`` and ``InformeService.procesar_revision_informe``)
with the body as their POST, so the role check, the state check, the services and the
flash messages are the native ones; nothing is validated or decided here. Access is the
native URL guard (kept access gaps included) plus the session CSRF check of every web
POST. The DOCX files are stored by the backend exactly as today.

Outcomes: 200 ``{success: true, messages, redirect}``; 400 with the same body and
``success: false`` when the native handler answered with an error message (nothing is
changed); 403 when the native handler answered 403; 404 for an unknown report.
The flash messages are returned and queued again, so the page the browser opens at
``redirect`` shows them once, as the native redirect does.
"""

import copy

from django.contrib import messages as django_messages
from django.core.exceptions import ObjectDoesNotExist
from django.http import QueryDict
from django.urls import reverse
from django.utils.datastructures import MultiValueDict
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import NotFound, ParseError
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.views import APIView

from core.web_gate import WebGatePermission
from admisiones.services.informes_service.impl import InformeService
from admisiones.views.web_views import InformeTecnicoDetailView
from admisiones.web_api_informes import VerInforme
from admisiones.web_api_templates import _native, pending_messages

LEVELS = {
    "success": django_messages.SUCCESS,
    "error": django_messages.ERROR,
    "warning": django_messages.WARNING,
}


def queue_again(request, mensajes):
    """Keep the flash messages for the page the browser opens next."""
    for mensaje in mensajes:
        django_messages.add_message(
            request._request,  # pylint: disable=protected-access
            LEVELS.get(mensaje["level"], django_messages.INFO),
            mensaje["message"],
        )


def post_request(request, data, files=None):
    """The Django request of the native handler, with ``data`` as its POST."""
    copia = copy.copy(request._request)  # pylint: disable=protected-access
    copia.method = "POST"
    copia.POST = data
    copia._files = files or MultiValueDict()  # pylint: disable=protected-access
    return copia


def _informe(request, tipo, pk):
    vista = _native(InformeTecnicoDetailView, request, tipo=tipo, pk=pk)
    try:
        return vista, vista.get_queryset().get(pk=pk)
    except ObjectDoesNotExist as exc:
        raise NotFound() from exc


def _detalle_url(tipo, informe):
    return reverse("informe_tecnico_ver", kwargs={"tipo": tipo, "pk": informe.pk})


def _answer(request, mensajes, redirect, ok=None):
    error = any(m["level"] == "error" for m in mensajes)
    exito = (not error) if ok is None else ok
    queue_again(request, mensajes)
    return Response(
        {"success": exito, "messages": mensajes, "redirect": redirect},
        status=200 if exito else 400,
    )


class InformeDocxEditadoWebView(APIView):
    """``POST .../informes/<tipo>/<pk>/docx-editado/``."""

    authentication_classes = [SessionAuthentication]
    permission_classes = [WebGatePermission, VerInforme]
    renderer_classes = [JSONRenderer]
    http_method_names = ["post"]

    def post(self, request, tipo, pk):
        vista, informe = _informe(request, tipo, pk)
        datos = QueryDict(mutable=True)
        datos["subir_docx"] = ""
        nativa = post_request(request, datos, request.FILES)
        vista.request = nativa
        respuesta = (
            vista._handle_subir_docx_editado_post(  # pylint: disable=protected-access
                nativa, tipo, informe
            )
        )
        if respuesta.status_code == 403:
            return Response({"success": False, "messages": []}, status=403)
        return _answer(request, pending_messages(request), _detalle_url(tipo, informe))


class InformeRevisionWebView(APIView):
    """``POST .../informes/<tipo>/<pk>/revision/``."""

    authentication_classes = [SessionAuthentication]
    permission_classes = [WebGatePermission, VerInforme]
    renderer_classes = [JSONRenderer]
    http_method_names = ["post"]

    def post(self, request, tipo, pk):
        body = request.data
        if not isinstance(body, dict):
            raise ParseError("El cuerpo debe ser un objeto.")
        datos = QueryDict(mutable=True)
        for nombre in ("estado", "observacion"):
            valor = body.get(nombre, "")
            if not isinstance(valor, str):
                raise ParseError(f"{nombre} debe ser texto.")
            datos[nombre] = valor
        campos = body.get("campos_a_subsanar", [])
        if not isinstance(campos, list) or not all(isinstance(c, str) for c in campos):
            raise ParseError("campos_a_subsanar debe ser una lista de textos.")
        datos.setlist("campos_a_subsanar", campos)
        _, informe = _informe(request, tipo, pk)
        InformeService.procesar_revision_informe(
            post_request(request, datos), tipo, informe
        )
        return Response(
            {
                "success": True,
                "messages": pending_messages(request),
                "redirect": reverse(
                    "admisiones_tecnicos_editar", args=[informe.admision_id]
                ),
            }
        )
