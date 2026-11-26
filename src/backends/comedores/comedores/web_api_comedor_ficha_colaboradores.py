"""Web API (G1 v1) of «Eliminar» a colaborador from the comedor ficha (CO07.01).

``POST /api/web/comedores/comedores/<pk>/colaboradores/<colaborador_id>/baja/`` runs
the native ``ColaboradorEspacioService.soft_delete`` for a colaborador of the comedor
the user's scope resolves (outside it, or a colaborador of another comedor, is a 404),
with the access of the native route (``comedores.delete_colaboradorespacio``). The
service sets the ``fecha_baja`` (it is idempotent for an inactive one); the native
message stays queued for the ficha the answer redirects to, exactly as the native
``redirect("comedor_detalle")``.
"""

from django.contrib import messages
from django.urls import reverse
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import NotFound
from rest_framework.permissions import BasePermission
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.views import APIView

from comedores.models import ColaboradorEspacio
from comedores.services.colaborador_espacio_service import ColaboradorEspacioService
from comedores.services.comedor_service import ComedorService
from comedores.web_api_comedores import MESSAGE_LEVELS
from core.decorators import _has_any_permissions
from core.web_gate import WebGatePermission

# The exact predicate of the native URL decorator.
BAJA_PERMISSIONS = ["comedores.delete_colaboradorespacio"]


class BajaColaborador(BasePermission):
    def has_permission(self, request, view):
        return _has_any_permissions(request.user, BAJA_PERMISSIONS)


class ComedorColaboradorBajaWebView(APIView):
    """``POST``: dar de baja a un colaborador del espacio."""

    authentication_classes = [SessionAuthentication]
    permission_classes = [WebGatePermission, BajaColaborador]
    renderer_classes = [JSONRenderer]
    http_method_names = ["post"]

    def post(self, request, pk, colaborador_id):
        comedor = ComedorService.get_scoped_comedor_or_404(pk, request.user)
        colaborador = (
            ColaboradorEspacio.objects.filter(pk=colaborador_id, comedor=comedor)
            .select_related("ciudadano")
            .first()
        )
        if not colaborador:
            raise NotFound()
        resultado = ColaboradorEspacioService.soft_delete(
            colaborador=colaborador, actor=request.user
        )
        nivel = messages.SUCCESS if resultado.get("success") else messages.WARNING
        # The native view queues the message for the ficha it redirects to.
        messages.add_message(
            request._request,  # pylint: disable=protected-access
            nivel,
            resultado["message"],
        )
        return Response(
            {
                "success": bool(resultado.get("success")),
                "redirect": reverse("comedor_detalle", kwargs={"pk": comedor.pk}),
                "message": {
                    "level": MESSAGE_LEVELS.get(nivel, "info"),
                    "text": str(resultado["message"]),
                },
            }
        )
