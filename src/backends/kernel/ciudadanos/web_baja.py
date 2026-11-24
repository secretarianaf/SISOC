"""Baja de un ciudadano para React (C05.03, G1 v1).

``/api/web/ciudadanos/<pk>/baja/`` lo sirve el core. Corre ``CiudadanosDeleteView``
con el mismo orden que la vista nativa: permiso ``ciudadanos.delete_ciudadano``
(403, también para un id inexistente) y después el 404. El ``GET`` proyecta el
contexto de la confirmación (``components/delete_confirm.html``); el ``POST`` corre
su ``post()``: baja lógica en cascada, mensaje en cola y redirección a la lista.
"""

from django.http import Http404
from django.utils.cache import patch_cache_control, patch_vary_headers
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.views import APIView

from ciudadanos.views import CiudadanosDeleteView
from ciudadanos.web_ficha import pending_messages
from core.web_gate import WebGatePermission


def _vista_baja(request, pk):
    if not request.user.has_perm("ciudadanos.delete_ciudadano"):
        raise PermissionDenied()
    vista = CiudadanosDeleteView()
    # pylint: disable-next=protected-access
    vista.setup(request._request, pk=pk)
    try:
        vista.object = vista.get_object()
    except Http404 as exc:
        raise NotFound() from exc
    return vista


def _previsualizacion(preview):
    return {
        "total_afectados": preview["total_afectados"],
        "total_baja_logica": preview["total_baja_logica"],
        "total_borrado_fisico": preview["total_borrado_fisico"],
        "desglose": [
            {
                "modelo": fila["modelo"],
                "cantidad": fila["cantidad"],
                "baja_logica": fila["modo"] == "baja_logica",
                "ejemplos": [str(e) for e in fila["ejemplos"]],
            }
            for fila in preview["desglose_por_modelo"]
        ],
    }


class CiudadanoBajaWebView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [WebGatePermission]
    renderer_classes = [JSONRenderer]
    http_method_names = ["get", "post"]

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        patch_cache_control(response, private=True, no_store=True)
        patch_vary_headers(response, ("Cookie",))
        return response

    def get(self, request, pk):
        vista = _vista_baja(request, pk)
        contexto = vista.get_context_data()
        return Response(
            {
                "id": vista.object.pk,
                # ``{{ object_name|upper }}`` del componente.
                "nombre_mayusculas": str(vista.object).upper(),
                "cancelar_url": vista.object.get_absolute_url(),
                "cascade_preview": _previsualizacion(contexto["cascade_preview"]),
                "messages": pending_messages(request),
            }
        )

    def post(self, request, pk):
        vista = _vista_baja(request, pk)
        # pylint: disable-next=protected-access
        respuesta = vista.post(request._request, pk=pk)
        return Response({"ok": True, "redirect": respuesta["Location"]})
