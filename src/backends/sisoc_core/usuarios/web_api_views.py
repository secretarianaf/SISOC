"""Session-only core web API, separate from the PWA token contract."""

from django.utils.cache import patch_cache_control, patch_vary_headers
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from drf_spectacular.openapi import AutoSchema
from drf_spectacular.utils import extend_schema
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import NotAuthenticated
from rest_framework.permissions import IsAuthenticated
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.views import APIView

from usuarios.web_api_serializers import (
    WebSessionContextSerializer,
    WebSessionErrorSerializer,
)
from usuarios.web_context import build_web_context


class WebSessionSchema(AutoSchema):
    """Do not advertise the project's global API-key alternative on this API."""

    def get_auth(self):
        # Register the standard SessionAuthentication component first.
        super().get_auth()
        return [{"cookieAuth": []}]


@method_decorator(ensure_csrf_cookie, name="dispatch")
class WebSessionView(APIView):
    """Read-only context for an active Django session, never a PWA token."""

    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]
    renderer_classes = [JSONRenderer]
    http_method_names = ["get", "head", "options"]
    schema = WebSessionSchema()

    @extend_schema(
        responses={200: WebSessionContextSerializer, 401: WebSessionErrorSerializer}
    )
    def get(self, request):
        context = build_web_context(request)
        if context is None:
            raise NotAuthenticated()
        return Response(WebSessionContextSerializer(context).data)

    def get_authenticate_header(self, request):
        return "Session"

    def handle_exception(self, exc):
        response = super().handle_exception(exc)
        if isinstance(exc, NotAuthenticated):
            response.data = {"detail": "Inicie sesión para continuar."}
        return response

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        patch_cache_control(response, private=True, no_store=True)
        patch_vary_headers(response, ("Cookie",))
        return response
