"""Web API (G1 v1) of the comedor intervention form (CO02): create, edit, subtypes.

Each endpoint runs the native view itself: GET returns what ``intervencion_form.html``
renders from ``get_context_data()``; POST (multipart or urlencoded, never JSON) runs
the native ``post()`` (``IntervencionForm``, the admission check, ``safe_redirect``
with ``next``, the file storage). A 302 becomes ``{"ok": true, "redirect": ...}``; a
rejected form returns 400 with the bound payload, as the native page re-renders it.
Permissions are the codes of the native URLs; no scope is added.

Native quirks kept: the date input value is the localized ``dd/mm/yyyy`` text, which
a ``type=date`` input shows empty; the template draws no error messages, so the
payload carries only the ``aria-invalid`` state; an unknown comedor or intervention
is a 404 (natively a 500 for the comedor).
"""

from django.http import Http404
from rest_framework.exceptions import NotFound
from rest_framework.response import Response

from comedores.models import Comedor
from core.web_gate import WebGatePermission
from intervenciones.views import (
    IntervencionCreateView,
    IntervencionUpdateView,
    sub_estados_intervenciones_ajax,
)
from intervenciones.web_api import (
    NativeWebView,
    comedor_ref,
    pending_messages,
    requires_any,
)

PERMISO_ALTA = ["intervenciones.add_intervencion"]
PERMISO_EDICION = ["intervenciones.change_intervencion"]
SELECTS = ("tipo_intervencion", "subintervencion", "destinatario", "forma_contacto")
FORMATOS = ("multipart/form-data", "application/x-www-form-urlencoded")


def _opciones(campo):
    return [
        {"value": str(valor), "label": str(texto)} for valor, texto in campo.choices
    ]


def _campo(form, nombre):
    bf = form[nombre]
    campo = {
        "id": bf.id_for_label,
        "label": str(bf.label),
        "required": bf.field.required,
        # Django 5 adds ``aria-invalid`` to the bound widget of an invalid field.
        "invalid": form.is_bound and bool(bf.errors),
    }
    valor = bf.value()
    if nombre in SELECTS:
        campo["options"] = _opciones(bf.field)
        campo["value"] = "" if valor in (None, "") else str(valor)
    elif nombre == "fecha":
        campo["value"] = bf.field.widget.format_value(valor) or ""
        campo["hidden_initial"] = bf.field.hidden_widget().format_value(valor) or ""
    elif nombre == "tiene_documentacion":
        campo["value"] = bool(valor)
    elif nombre == "observaciones":
        campo["value"] = valor or ""
    return campo


def formulario(contexto, request):
    form = contexto["form"]
    comedor = contexto["object"]
    return {
        "comedor": comedor_ref(comedor),
        "admision_id": contexto.get("admision_id"),
        "fields": {
            nombre: _campo(form, nombre)
            for nombre in (*SELECTS, "fecha", "observaciones", "tiene_documentacion")
        }
        | {
            "documentacion": {
                "id": form["documentacion"].id_for_label,
                "label": str(form["documentacion"].label),
            }
        },
        "messages": pending_messages(request),
    }


class _FormularioWebView(NativeWebView):
    http_method_names = ["get", "post", "head"]

    def _vista(self, request, **kwargs):
        raise NotImplementedError

    def get(self, request, **kwargs):
        vista = self._vista(request, **kwargs)
        try:
            contexto = vista.get_context_data()
        except Comedor.DoesNotExist as exc:
            raise NotFound() from exc
        return Response(formulario(contexto, request))

    def post(self, request, **kwargs):
        # ``Request.content_type`` keeps the multipart boundary; Django strips it.
        # pylint: disable-next=protected-access
        if request._request.content_type not in FORMATOS:
            return Response({"detail": "Formato de solicitud no admitido."}, status=415)
        vista = self._vista(request, **kwargs)
        try:
            # pylint: disable-next=protected-access
            respuesta = vista.post(request._request)
        except Comedor.DoesNotExist as exc:
            raise NotFound() from exc
        except Http404 as exc:
            raise NotFound() from exc
        if respuesta.status_code == 302:
            return Response({"ok": True, "redirect": respuesta["Location"]})
        return Response(formulario(respuesta.context_data, request), status=400)


class IntervencionCrearWebView(_FormularioWebView):
    """``/api/web/comedores/intervenciones/comedor/<pk>/crear/``: ``IntervencionCreateView``."""

    permission_classes = [WebGatePermission, requires_any(PERMISO_ALTA)]

    def _vista(self, request, **kwargs):
        vista = self.native(IntervencionCreateView, request, **kwargs)
        vista.object = None
        return vista


class IntervencionEditarWebView(_FormularioWebView):
    """``/api/web/comedores/intervenciones/<pk>/editar/<pk2>/``: ``IntervencionUpdateView``."""

    permission_classes = [WebGatePermission, requires_any(PERMISO_EDICION)]

    def _vista(self, request, **kwargs):
        vista = self.native(IntervencionUpdateView, request, **kwargs)
        try:
            vista.object = vista.get_object()
        except Http404 as exc:
            raise NotFound() from exc
        return vista


class SubestadosWebView(NativeWebView):
    """``GET .../intervenciones/subestados/?id=``: the native subtype JSON, unchanged.

    The native route only asks for a signed-in user, so no permission is added.
    """

    permission_classes = [WebGatePermission]

    def get(self, request):
        # pylint: disable-next=protected-access
        return sub_estados_intervenciones_ajax(request._request)
