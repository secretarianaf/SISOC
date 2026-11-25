"""Web API (G1 v1) that saves the technical-report form (AD02.01, U3a).

``POST /api/web/comedores/admisiones/informes/<tipo>/admision/<admision_id>/guardar/``
(create) and ``POST .../<tipo>/<pk>/guardar/`` (edit) accept
``{"action": "draft"|"submit", "values": {<field>: <value>}}`` and run the native
pipeline unchanged: the native view's ``get_form`` (so ``require_full`` follows the
action and only the effective fields are read; unknown keys are ignored),
``form.is_valid()`` and ``InformeService.guardar_informe``. Nothing is validated or
decided here. Access is the native URL guard (kept access gaps included) plus the
session CSRF check of every web POST.

Outcomes:

* 200 ``success``: report saved, ``redirect`` is the native success URL.
* 200 ``success: false`` + ``saved_as_draft``: the template publication failed and
  the report was kept as a draft (native behaviour).
* 400: invalid action or invalid form (nothing is persisted); ``fields`` is the
  bound form so the editor can show every error.
* 409: the service rejected the save before writing (missing or unaccepted
  documents, validated report).

Native parity: the endpoint adds no transaction of its own. ``guardar_informe`` is
``@transaction.atomic``, so when the DOCX generation fails its
``transaction.set_rollback(True)`` rolls the whole save back (no report, admission
state unchanged), exactly as on the Django page;
``test_generation_failure_matches_the_native_view`` pins both sides.
"""

import copy

from django.http import QueryDict
from django.urls import reverse
from django.utils.datastructures import MultiValueDict
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import ParseError
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.views import APIView

from core.web_gate import WebGatePermission
from admisiones.services.informes_service.impl import InformeService
from admisiones.views.web_views import _collect_form_errors_for_messages
from admisiones.web_api_informe_formulario import (
    fields_payload,
    prepare_native_view,
)
from admisiones.web_api_informes import VerInforme

ACTIONS = ("draft", "submit")
INVALID_PREFIX = "No se pudo guardar el informe. "


def _post_data(body):
    """Form-encoded view of the JSON ``values`` (a checkbox is sent only when on)."""
    values = body.get("values")
    if not isinstance(values, dict):
        raise ParseError("values debe ser un objeto.")
    data = QueryDict(mutable=True)
    for name, value in values.items():
        if value is True:
            data[name] = "on"
        elif value is None or value is False:
            continue
        elif isinstance(value, (str, int, float)):
            data[name] = str(value)
        else:
            raise ParseError(f"Valor inválido para {name}.")
    data["action"] = body["action"]
    return data


def _native_post_view(request, tipo, admision_id, pk, data):
    """The native view with the JSON body as its POST (the form reads it)."""
    post_request = copy.copy(request._request)  # pylint: disable=protected-access
    post_request.method = "POST"
    post_request.POST = data
    post_request._files = MultiValueDict()  # pylint: disable=protected-access
    probe = prepare_native_view(request, tipo, admision_id, pk)
    kwargs = {"tipo": tipo, **probe.kwargs}
    vista = type(probe)()
    vista.setup(post_request, **kwargs)
    vista.object = probe.object
    for name in ("admision_obj", "tipo"):
        if hasattr(probe, name):
            setattr(vista, name, getattr(probe, name))
    return vista


def _invalid_message(form):
    errores = _collect_form_errors_for_messages(form)
    if errores:
        return f"{INVALID_PREFIX}Revisá los campos: " + " | ".join(errores)
    return f"{INVALID_PREFIX}Verificá que los campos obligatorios estén completos."


class InformeGuardarWebView(APIView):
    """Draft and submit of the create and edit pages."""

    authentication_classes = [SessionAuthentication]
    permission_classes = [WebGatePermission, VerInforme]
    renderer_classes = [JSONRenderer]
    http_method_names = ["post"]

    def post(self, request, tipo, admision_id=None, pk=None):
        body = request.data
        if not isinstance(body, dict) or body.get("action") not in ACTIONS:
            raise ParseError("action debe ser draft o submit.")
        vista = _native_post_view(request, tipo, admision_id, pk, _post_data(body))
        creacion = admision_id is not None
        form = vista.get_form()
        if not form.is_valid():
            return Response(
                {
                    "success": False,
                    "message": _invalid_message(form),
                    "fields": fields_payload(form),
                    "non_field_errors": list(form.non_field_errors()),
                },
                status=400,
            )
        if creacion:
            form.instance.tipo = vista.tipo
        admision = vista.admision_obj if creacion else form.instance.admision
        resultado = InformeService.guardar_informe(
            form,
            admision,
            es_creacion=creacion,
            action=body["action"],
            usuario=request.user,
        )
        if resultado.get("success"):
            informe = resultado["informe"]
            return Response(
                {
                    "success": True,
                    "informe_id": informe.pk,
                    "estado": informe.estado,
                    "estado_formulario": informe.estado_formulario,
                    "redirect": reverse(
                        "admisiones_tecnicos_editar", args=[admision.pk]
                    ),
                }
            )
        error = resultado.get("error", "No se pudo guardar el informe técnico.")
        if resultado.get("saved_as_draft"):
            return Response({"success": False, "saved_as_draft": True, "error": error})
        return Response(
            {"success": False, "saved_as_draft": False, "error": error}, status=409
        )
