"""Web API (G1 v1) of the documentation of an admision: upload, extra document, delete (AD02.03).

``POST .../admisiones/<admision_id>/documentacion/<documentacion_id>/subir/`` (multipart
``archivo``), ``POST .../admisiones/<admision_id>/documentacion/personalizada/agregar/``
(multipart ``nombre`` and ``archivo``) and
``DELETE .../admisiones/<admision_id>/documentacion/<id>/eliminar/?archivo_id=&preview=``
run the native view functions ``subir_archivo_admision``,
``crear_documento_personalizado`` and ``eliminar_archivo_admision`` with the request as
their own, so the role vetoes, the technician window, the state guards, ``update_or_create``,
the post-processing, the cleaning of the IF/GDE numbers, the soft delete and every message
are the native ones; nothing is validated or decided here.

The answer is the native JSON without its ``html`` member: React builds the row from the
data (``documento``, ``row_id``, ``estado_display``, ``estado_valor``, ``archivo_id``) and
does not keep the Django presentation. The access is exactly the native one (only a logged-in
user: the gaps of the contract are kept) plus the session CSRF check of every web POST and
DELETE. The files are stored by the backend as today.
"""

import json

from rest_framework.authentication import SessionAuthentication
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.views import APIView

from core.web_gate import WebGatePermission
from admisiones.views.web_views import (
    crear_documento_personalizado,
    eliminar_archivo_admision,
    subir_archivo_admision,
)


def _answer(respuesta):
    """The native JSON answer without the Django markup of the row."""
    datos = json.loads(respuesta.content)
    datos.pop("html", None)
    return Response(datos, status=respuesta.status_code)


class DocumentosBaseWebView(APIView):
    """Common settings: the native views only require a logged-in user."""

    authentication_classes = [SessionAuthentication]
    permission_classes = [WebGatePermission]
    renderer_classes = [JSONRenderer]

    @staticmethod
    def _nativa(request):
        return request._request  # pylint: disable=protected-access


class DocumentoSubirWebView(DocumentosBaseWebView):
    """``POST .../<admision_id>/documentacion/<documentacion_id>/subir/``."""

    http_method_names = ["post"]

    def post(self, request, admision_id, documentacion_id):
        return _answer(
            subir_archivo_admision(self._nativa(request), admision_id, documentacion_id)
        )


class DocumentoPersonalizadoWebView(DocumentosBaseWebView):
    """``POST .../<admision_id>/documentacion/personalizada/agregar/``."""

    http_method_names = ["post"]

    def post(self, request, admision_id):
        return _answer(
            crear_documento_personalizado(self._nativa(request), admision_id)
        )


class DocumentoEliminarWebView(DocumentosBaseWebView):
    """``DELETE .../<admision_id>/documentacion/<documentacion_id>/eliminar/``."""

    http_method_names = ["delete"]

    def delete(self, request, admision_id, documentacion_id):
        return _answer(
            eliminar_archivo_admision(
                self._nativa(request), admision_id, documentacion_id
            )
        )
