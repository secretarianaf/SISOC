"""Web API (G1 v1) of the comedor validation (CO07.03): ``/api/web/comedores/comedores/``.

``POST .../<pk>/validar/`` runs the native ``validar_comedor`` view unchanged
(object scope, ``ValidacionService`` capability and rules, the atomic estado
update with its history row, the native flash message and the ``safe_redirect``
of ``next``). After the web gate only the native URL guard is added
(``permissions_any_required`` of ``comedores.view_comedor``,
``admisiones.view_admision`` and ``acompanamientos.view_informacionrelevante``).
The message stays queued for the page the redirect lands on, as in the native
flow; a refused action (no capability, no option, "otro" without comment,
unknown action) answers the same redirect and changes nothing.

``GET .../<pk>/validacion/`` gives the modals' data: the capability computed by
``ValidacionService.puede_validar`` (React never replicates the role set) and
the ``HistorialValidacion`` choices the native ficha passes as
``opciones_no_validar``.
"""

from rest_framework.authentication import SessionAuthentication
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.views import APIView

from core.web_gate import WebGatePermission
from comedores.models import HistorialValidacion
from comedores.services.comedor_service import ComedorService
from comedores.services.validacion_service import ValidacionService
from comedores.views.validacion import validar_comedor
from comedores.web_api_comedores import VerComedores
from django.urls import reverse


class _ValidacionView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [WebGatePermission, VerComedores]
    renderer_classes = [JSONRenderer]


class ComedorValidacionWebView(_ValidacionView):
    """``GET .../<pk>/validacion/``: capability and choices of the two modals."""

    http_method_names = ["get", "head"]

    def get(self, request, pk):
        comedor = ComedorService.get_scoped_comedor_or_404(pk, request.user)
        puede = bool(ValidacionService.puede_validar(request.user, comedor))
        return Response(
            {
                "id": comedor.pk,
                "puede_validar": puede,
                "opciones": (
                    [
                        {"value": value, "label": str(label)}
                        for value, label in HistorialValidacion.get_opciones_no_validar()
                    ]
                    if puede
                    else []
                ),
                "urls": {
                    "ficha": reverse("comedor_detalle", kwargs={"pk": comedor.pk})
                },
            }
        )


class ComedorValidarWebView(_ValidacionView):
    """``POST .../<pk>/validar/``: the native view, answered as ``{"redirect": url}``."""

    http_method_names = ["post"]

    def post(self, request, pk):
        respuesta = validar_comedor(
            request._request, pk=pk  # pylint: disable=protected-access
        )
        return Response({"redirect": respuesta.url})
