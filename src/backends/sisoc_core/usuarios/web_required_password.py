"""Session-only metadata and action for the mandatory-password React page."""

# Explicit transport DTOs share the existing session whitelist.
# pylint: disable=abstract-method
from django.contrib.auth.forms import SetPasswordForm
from django.urls import reverse
from django.utils.cache import patch_cache_control, patch_vary_headers
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from drf_spectacular.utils import PolymorphicProxySerializer, extend_schema
from rest_framework import serializers
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import PermissionDenied
from rest_framework.parsers import FormParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.views import APIView

from usuarios.required_password_change import complete_required_password_change
from usuarios.web_api_serializers import (
    WebAccessSerializer,
    WebNavigationNodeSerializer,
    WebUserSerializer,
)
from usuarios.web_api_views import WebSessionSchema
from usuarios.web_context import build_web_context
from usuarios.web_navigation import build_web_navigation
from usuarios.web_session import resolve_web_access


class RequiredPasswordRequestSerializer(serializers.Serializer):
    new_password1 = serializers.CharField(write_only=True, trim_whitespace=False)
    new_password2 = serializers.CharField(write_only=True, trim_whitespace=False)


class PasswordFieldSerializer(serializers.Serializer):
    name = serializers.ChoiceField(choices=["new_password1", "new_password2"])
    label = serializers.CharField()
    help_text = serializers.CharField(allow_blank=True)
    required = serializers.BooleanField()


class RequiredPasswordPresentationSerializer(serializers.Serializer):
    user = WebUserSerializer()
    footer_version_label = serializers.CharField()
    legacy_frame_navigation = WebNavigationNodeSerializer(many=True)


class RequiredPasswordMetadataSerializer(serializers.Serializer):
    access = WebAccessSerializer()
    fields = PasswordFieldSerializer(many=True)
    presentation = RequiredPasswordPresentationSerializer()


class RequiredPasswordSuccessSerializer(serializers.Serializer):
    ok = serializers.BooleanField()
    redirect = serializers.CharField()
    message = serializers.CharField(required=False)


class RequiredPasswordErrorSerializer(serializers.Serializer):
    detail = serializers.CharField(required=False)
    state = serializers.CharField(required=False)
    required_action_url = serializers.CharField(required=False, allow_null=True)
    errors = serializers.JSONField(required=False)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class RequiredPasswordChangeWebView(APIView):
    """Resolve this prerequisite without requiring business-ready access."""

    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = [FormParser]
    renderer_classes = [JSONRenderer]
    http_method_names = ["get", "head", "post", "options"]
    schema = WebSessionSchema()
    access = None

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        self.access = resolve_web_access(request)
        if self.access.state == "web_access_denied":
            raise PermissionDenied("Este usuario no tiene acceso SISOC web habilitado.")

    def get_authenticate_header(self, request):
        return "Session"

    def handle_exception(self, exc):
        response = super().handle_exception(exc)
        if self.access is not None and self.access.state == "web_access_denied":
            response.data = {
                "detail": str(exc.detail),
                "state": self.access.state,
                "required_action_url": self.access.required_action_url,
            }
        return response

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        patch_cache_control(response, private=True, no_store=True)
        patch_vary_headers(response, ("Cookie",))
        return response

    @staticmethod
    def completed_response():
        return Response({"ok": True, "redirect": reverse("inicio")})

    @extend_schema(
        responses={
            200: PolymorphicProxySerializer(
                component_name="RequiredPasswordRead",
                serializers=[
                    RequiredPasswordMetadataSerializer,
                    RequiredPasswordSuccessSerializer,
                ],
                resource_type_field_name=None,
            ),
            401: RequiredPasswordErrorSerializer,
            403: RequiredPasswordErrorSerializer,
        }
    )
    def get(self, request):
        if self.access.state != "password_change_required":
            return self.completed_response()
        form = SetPasswordForm(request.user)
        context = build_web_context(request)
        payload = {
            "access": context["access"],
            "fields": [
                {
                    "name": name,
                    "label": str(field.label),
                    "help_text": str(field.help_text),
                    "required": field.required,
                }
                for name, field in form.fields.items()
            ],
            "presentation": {
                "user": context["user"],
                "footer_version_label": context["footer_version_label"],
                # Presentation matches existing HTML; it never authorizes actions.
                "legacy_frame_navigation": build_web_navigation(request),
            },
        }
        return Response(RequiredPasswordMetadataSerializer(payload).data)

    @extend_schema(
        request=RequiredPasswordRequestSerializer,
        responses={
            200: RequiredPasswordSuccessSerializer,
            400: RequiredPasswordErrorSerializer,
            401: RequiredPasswordErrorSerializer,
            403: RequiredPasswordErrorSerializer,
            415: RequiredPasswordErrorSerializer,
        },
    )
    def post(self, request):
        data = request.data
        if self.access.state != "password_change_required":
            return self.completed_response()
        form = SetPasswordForm(request.user, data)
        if not form.is_valid():
            return Response({"errors": form.errors.get_json_data()}, status=400)
        complete_required_password_change(request, form)
        return Response(
            {
                "ok": True,
                "message": "Contraseña actualizada correctamente.",
                "redirect": reverse("inicio"),
            }
        )
