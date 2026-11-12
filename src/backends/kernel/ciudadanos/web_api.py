"""Ficha Ciudadano 360 para React (C05.01, parte que C04 necesita; G1 v1).

``GET /api/web/ciudadanos/<pk>/`` lo sirve el core: ``ciudadanos`` no es un
backend registrado, así que el proxy no lo reenvía. Mismo permiso y mismo 404
que ``CiudadanosDetailView``. Hoy entrega el encabezado de la ficha y la lista
``aportes`` armada en el servidor (``aportes_web_de_ciudadano``); el resto de la
ficha sigue en Django hasta que se migre.
"""

from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils.cache import patch_cache_control, patch_vary_headers
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import NotFound
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.views import APIView

from ciudadanos.detail_contributions import aportes_web_de_ciudadano
from ciudadanos.models import Ciudadano
from ciudadanos.web_aportes import PuedeVerCiudadano
from core.web_gate import WebGatePermission


class CiudadanoFichaWebView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [WebGatePermission, PuedeVerCiudadano]
    renderer_classes = [JSONRenderer]
    http_method_names = ["get", "head", "options"]

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        patch_cache_control(response, private=True, no_store=True)
        patch_vary_headers(response, ("Cookie",))
        return response

    def get(self, request, pk):
        try:
            ciudadano = get_object_or_404(Ciudadano, pk=pk)
        except Http404 as exc:
            raise NotFound() from exc
        return Response(
            {
                "id": ciudadano.pk,
                "nombre": ciudadano.nombre,
                "apellido": ciudadano.apellido,
                "tipo_documento_texto": ciudadano.get_tipo_documento_display(),
                "numero_documento": (
                    str(ciudadano.numero_documento)
                    if ciudadano.numero_documento
                    else None
                ),
                "pais_emisor": (
                    str(ciudadano.pais_emisor) if ciudadano.pais_emisor else None
                ),
                "identificador_interno": ciudadano.identificador_interno,
                "aportes": aportes_web_de_ciudadano(ciudadano.pk),
            }
        )
