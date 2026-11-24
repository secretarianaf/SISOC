"""Base común de las APIs web de gestión de ciudadanos (C01-C03; G1 v1).

Corre la vista nativa con su ``dispatch`` (login, permiso y 404 en su orden) y deja
que cada pantalla proyecte el contexto o la redirección que esa vista devolvió.
"""

from django.http import Http404
from django.utils.cache import patch_cache_control, patch_vary_headers
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import NotFound
from rest_framework.renderers import JSONRenderer
from rest_framework.views import APIView

from core.web_gate import WebGatePermission


class VistaNativaWebView(APIView):
    """APIView del core que despacha una vista nativa de Django."""

    authentication_classes = [SessionAuthentication]
    permission_classes = [WebGatePermission]
    renderer_classes = [JSONRenderer]
    vista_nativa = None

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        patch_cache_control(response, private=True, no_store=True)
        patch_vary_headers(response, ("Cookie",))
        return response

    def despachar(self, request, **kwargs):
        """Respuesta de ``dispatch`` de la vista nativa; su 404 pasa a 404 de DRF."""
        # pylint: disable-next=not-callable
        vista = self.vista_nativa()
        # pylint: disable-next=protected-access
        django_request = request._request
        vista.setup(django_request, **kwargs)
        try:
            return vista.dispatch(django_request, **kwargs)
        except Http404 as exc:
            raise NotFound() from exc
