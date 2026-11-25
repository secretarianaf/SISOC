"""Desvinculación de un familiar para React (C03.02; G1 v1).

``/api/web/ciudadanos/familiares/<pk>/eliminar/`` lo sirve el core y corre
``GrupoFamiliarDeleteView`` con su ``dispatch``: permiso ``ciudadanos.change_ciudadano``
(403, también para un id inexistente) y después el 404 de la relación (la ya dada de baja
también). El ``GET`` proyecta la confirmación de ``components/delete_confirm.html`` con la
vista previa de cascada; el ``POST`` corre su ``post()``: baja lógica de la relación,
«Relación familiar eliminada.» en cola y redirección a ``next`` (ruta interna) o a la ficha
del ciudadano 1. El ``next`` viaja en la query, como en la vista nativa.
"""

from django.utils.http import url_has_allowed_host_and_scheme
from rest_framework.response import Response

from ciudadanos.views import GrupoFamiliarDeleteView
from ciudadanos.web_baja import _previsualizacion
from ciudadanos.web_ficha import pending_messages
from ciudadanos.web_gestion_despacho import VistaNativaWebView


def _cancelar_url(request, relacion):
    """``next`` de la query si es una ruta interna segura; si no, la ficha del ciudadano 1."""
    destino = request.query_params.get("next")
    if (
        destino
        and destino.startswith("/")
        and url_has_allowed_host_and_scheme(destino, allowed_hosts={request.get_host()})
    ):
        return destino
    return relacion.ciudadano_1.get_absolute_url()


class GrupoFamiliarEliminarWebView(VistaNativaWebView):
    """``GET/POST /api/web/ciudadanos/familiares/<pk>/eliminar/``."""

    http_method_names = ["get", "post"]
    vista_nativa = GrupoFamiliarDeleteView

    def get(self, request, pk):
        respuesta = self.despachar(request, pk=pk)
        contexto = respuesta.context_data
        relacion = contexto["object"]
        return Response(
            {
                "id": relacion.pk,
                # ``{{ object_name|upper }}`` del componente.
                "nombre_mayusculas": str(relacion).upper(),
                "cancelar_url": _cancelar_url(request, relacion),
                "cascade_preview": _previsualizacion(contexto["cascade_preview"]),
                "messages": pending_messages(request),
            }
        )

    def post(self, request, pk):
        respuesta = self.despachar(request, pk=pk)
        return Response({"ok": True, "redirect": respuesta["Location"]})
