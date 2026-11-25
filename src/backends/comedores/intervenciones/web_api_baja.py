"""Web API (G1 v1) of the comedor intervention soft-delete confirmation (CO02).

``/api/web/comedores/intervenciones/comedor/<comedor_id>/baja/<intervencion_id>/``
runs ``IntervencionDeleteView`` itself: GET projects the confirmation page
(``intervencion_confirm_delete.html`` over ``components/delete_confirm.html``) and POST
runs the native ``post()`` (soft delete with the user, native message, redirect to the
list). The route keeps the native permission, ``comedores.delete_nomina``, which is
unrelated to interventions: the contract asks to characterize it, not to replace it.

Native quirks kept: the object is looked up by its id alone (``comedor_id`` is only the
return target and the breadcrumb), and the breadcrumb links the comedor page with the
intervention id.
"""

from django.http import Http404
from django.urls import reverse
from rest_framework.exceptions import NotFound
from rest_framework.response import Response

from core.web_gate import WebGatePermission
from intervenciones.views import IntervencionDeleteView
from intervenciones.web_api import NativeWebView, pending_messages, requires_any

PERMISO_BAJA = ["comedores.delete_nomina"]


def preview_json(preview):
    """The cascade preview of the native confirmation, as plain JSON."""
    if not preview:
        return None
    return {
        "total_afectados": preview.get("total_afectados", 0),
        "total_baja_logica": preview.get("total_baja_logica", 0),
        "total_borrado_fisico": preview.get("total_borrado_fisico", 0),
        "desglose_por_modelo": [
            {
                "modelo": str(item.get("modelo", "")),
                "cantidad": item.get("cantidad", 0),
                "modo": item.get("modo", ""),
                "ejemplos": [str(ejemplo) for ejemplo in item.get("ejemplos") or []],
            }
            for item in preview.get("desglose_por_modelo", [])
        ],
    }


def confirmacion(contexto, cancel_url, request):
    """What ``components/delete_confirm.html`` renders (``object_name|upper``)."""
    return {
        "id": contexto["object"].id,
        "object_name": str(contexto["object"]).upper(),
        "cascade_preview": preview_json(contexto.get("cascade_preview")),
        "confirm_text": str(contexto["confirm_text"]),
        "cancel_text": str(contexto["cancel_text"]),
        "cancel_url": cancel_url,
        "messages": pending_messages(request),
    }


class IntervencionBajaWebView(NativeWebView):
    """``/api/web/comedores/intervenciones/comedor/<comedor_id>/baja/<intervencion_id>/``."""

    permission_classes = [WebGatePermission, requires_any(PERMISO_BAJA)]
    http_method_names = ["get", "post", "head"]

    def _vista(self, request, comedor_id, intervencion_id):
        vista = self.native(
            IntervencionDeleteView,
            request,
            comedor_id=comedor_id,
            intervencion_id=intervencion_id,
        )
        try:
            vista.object = vista.get_object()
        except Http404 as exc:
            raise NotFound() from exc
        return vista

    def get(self, request, comedor_id, intervencion_id):
        vista = self._vista(request, comedor_id, intervencion_id)
        contexto = vista.get_context_data()
        objeto = contexto["object"]
        return Response(
            {
                **confirmacion(
                    contexto,
                    reverse("comedor_intervencion_ver", args=[comedor_id]),
                    request,
                ),
                "breadcrumb": {
                    "etiqueta": str(objeto),
                    "url": reverse("comedor_detalle", args=[objeto.id]),
                },
            }
        )

    def post(self, request, comedor_id, intervencion_id):
        vista = self._vista(request, comedor_id, intervencion_id)
        # pylint: disable-next=protected-access
        respuesta = vista.post(request._request)
        return Response({"ok": True, "redirect": respuesta["Location"]})
