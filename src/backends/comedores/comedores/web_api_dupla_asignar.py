"""Web API (G1 v1) of the comedor technical-team assignment screen (CO07).

``/api/web/comedores/asignar-dupla/<pk>/`` keeps the permission code of the native URL
``comedores/dupla/asignar/<pk>`` (``duplas.change_dupla``, superuser bypass included) and runs
the native ``AsignarDuplaListView`` itself: the scoped comedor lookup (a comedor outside the
user's scope is a 404), the active duplas, the assignment through
``ComedorService.asignar_dupla_a_comedor`` and its native messages. The native 302 becomes
``{"ok": true, "redirect": ...}``; the messages stay queued for the page it lands on.
"""

from django.http import Http404
from django.urls import reverse
from rest_framework.exceptions import NotFound
from rest_framework.response import Response

from intervenciones.web_api import (
    NativeWebView,
    comedor_ref,
    pending_messages,
    requires_any,
)
from comedores.views.dupla import AsignarDuplaListView
from core.web_gate import WebGatePermission

FORMATOS = ("multipart/form-data", "application/x-www-form-urlencoded")
ASSIGN_PERMISSIONS = ["duplas.change_dupla"]


class AsignarDuplaWebView(NativeWebView):
    """``GET/POST /api/web/comedores/asignar-dupla/<pk>/``: ``asignar_dupla_form.html``."""

    permission_classes = [WebGatePermission, requires_any(ASSIGN_PERMISSIONS)]
    http_method_names = ["get", "head", "post"]

    def _vista(self, request, pk):
        vista = self.native(AsignarDuplaListView, request, pk=pk)
        vista.object_list = vista.get_queryset()
        return vista

    def get(self, request, pk):
        vista = self._vista(request, pk)
        try:
            contexto = vista.get_context_data()
        except Http404 as exc:
            raise NotFound() from exc
        comedor = contexto["comedor"]
        return Response(
            {
                "comedor": comedor_ref(comedor),
                "dupla_actual_id": comedor.dupla_id,
                "duplas": [
                    {
                        "id": dupla.id,
                        "nombre": dupla.nombre,
                        "coordinador": dupla.coordinador_nombre,
                        "tecnicos": dupla.tecnicos_nombres,
                        "abogado": dupla.abogado_nombre,
                    }
                    for dupla in contexto["duplas"]
                ],
                "urls": {"comedores": reverse("comedores")},
                "messages": pending_messages(request),
            }
        )

    def post(self, request, pk):
        # ``Request.content_type`` keeps the multipart boundary; Django strips it.
        # pylint: disable-next=protected-access
        if request._request.content_type not in FORMATOS:
            return Response({"detail": "Formato de solicitud no admitido."}, status=415)
        vista = self._vista(request, pk)
        try:
            # pylint: disable-next=protected-access
            respuesta = vista.post(request._request)
        except Http404 as exc:
            raise NotFound() from exc
        return Response({"ok": True, "redirect": respuesta["Location"]})
