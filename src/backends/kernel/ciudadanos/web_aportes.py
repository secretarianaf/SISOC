"""Aportes de verticales a Ciudadano 360 en JSON (C04.01, G1 v1).

``GET /api/web/<backend>/ciudadanos/<pk>/aportes/<aporte>/`` lo sirve el
backend dueño del aporte. El core ya evaluó sesión y requisitos web y firmó el
pedido (``core.web_gate``); acá rigen el permiso de la ficha, la existencia del
ciudadano y el proyector que el dueño registró para ese aporte. El fragmento
HTML (``contribucion_detalle_ciudadano``) no cambia.
"""

import logging

from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils.cache import patch_cache_control, patch_vary_headers
from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import NotFound
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.views import APIView

from ciudadanos.detail_contributions import (
    APORTES_WEB,
    nombre_backend_de_aporte,
    proyector_de_aporte,
)
from ciudadanos.models import Ciudadano
from core.web_gate import WebGatePermission

logger = logging.getLogger("django")

DETAIL_NO_DISPONIBLE = "Aporte no disponible en este servicio."
DETAIL_SERVICIO = "Servicio no disponible."
CODIGO_APORTE_NO_DISPONIBLE = "aporte_no_disponible"


class PuedeVerCiudadano(BasePermission):
    """Mismo permiso que la ficha (``CiudadanosDetailView``)."""

    def has_permission(self, request, view):
        return request.user.has_perm("ciudadanos.view_ciudadano")


class AporteCiudadanoWebView(APIView):
    """Proyección JSON de un aporte; ``backend`` es la clave del dueño en la URL."""

    authentication_classes = [SessionAuthentication]
    permission_classes = [WebGatePermission, IsAuthenticated, PuedeVerCiudadano]
    renderer_classes = [JSONRenderer]
    http_method_names = ["get", "head", "options"]
    backend = ""

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        patch_cache_control(response, private=True, no_store=True)
        patch_vary_headers(response, ("Cookie",))
        return response

    def get(self, request, pk, aporte):
        # Sin parámetro de origen ni de sección: el aporte solo elige entre los
        # registrados en este proceso y que pertenecen al backend de la URL.
        proyector = proyector_de_aporte(aporte) if aporte in APORTES_WEB else None
        if proyector is None or nombre_backend_de_aporte(aporte) != self.backend:
            raise NotFound(DETAIL_NO_DISPONIBLE)
        try:
            ciudadano = get_object_or_404(Ciudadano, pk=pk)
        except Http404 as exc:
            raise NotFound() from exc
        try:
            secciones = proyector(ciudadano)
        except Exception:  # pylint: disable=broad-exception-caught
            logger.exception(
                "Error cargando aporte %s para ciudadano %s", aporte, ciudadano.pk
            )
            return Response(
                {"detail": DETAIL_SERVICIO, "codigo": CODIGO_APORTE_NO_DISPONIBLE},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        return Response({"aporte": aporte, "secciones": secciones})
