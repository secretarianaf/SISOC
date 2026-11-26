"""Web API (G1 v1) of the capacitaciones review from the comedor ficha (CO07.01).

``POST /api/web/comedores/comedores/<pk>/capacitaciones/<certificado_id>/estado/``
runs the native ``review_certificate`` for a certificate of the comedor the user's
scope resolves (outside it, or a certificate of another comedor, is a 404), with
the access of the native route (``comedores.change_comedor``). The answer keeps the
native JSON: ``{"success": true, "item": ...}`` or ``{"success": false, "error": ...}``
with a 400 when the service refuses (invalid state, a reviewed certificate that
changes, a rejection without observation), leaving the certificate unchanged.
"""

from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import BasePermission
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.views import APIView

from comedores.models import CapacitacionComedorCertificado
from comedores.services.capacitaciones_certificados_service import (
    review_certificate,
    serialize_certificate,
)
from comedores.services.comedor_service import ComedorService
from core.decorators import _has_any_permissions
from core.web_gate import WebGatePermission

# The exact predicate of the native URL decorator.
REVIEW_PERMISSIONS = ["comedores.change_comedor"]


class RevisarCapacitaciones(BasePermission):
    def has_permission(self, request, view):
        return _has_any_permissions(request.user, REVIEW_PERMISSIONS)


class ComedorCapacitacionEstadoWebView(APIView):
    """``POST``: accept or reject (with observation) a capacitación certificate."""

    authentication_classes = [SessionAuthentication]
    permission_classes = [WebGatePermission, RevisarCapacitaciones]
    renderer_classes = [JSONRenderer]
    http_method_names = ["post"]

    def post(self, request, pk, certificado_id):
        comedor = ComedorService.get_scoped_comedor_or_404(pk, request.user)
        certificado = get_object_or_404(
            CapacitacionComedorCertificado, pk=certificado_id, comedor=comedor
        )
        estado = (request.data.get("estado") or "").strip()
        observacion = request.data.get("observacion")
        try:
            review_certificate(
                certificado, estado, request.user, observacion=observacion
            )
        except ValidationError as exc:
            if hasattr(exc, "message_dict"):
                detalle = exc.message_dict
            elif hasattr(exc, "messages"):
                detalle = exc.messages
            else:
                detalle = str(exc)
            return Response(
                {"success": False, "error": detalle},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(
            {
                "success": True,
                "item": serialize_certificate(
                    certificado,
                    request=request._request,  # pylint: disable=protected-access
                ),
            }
        )
