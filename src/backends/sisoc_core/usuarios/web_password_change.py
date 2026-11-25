"""Session JSON transport over Django's unchanged voluntary-password view."""

# Output-only schemas do not implement persistence.
# pylint: disable=abstract-method
from django.contrib.auth.views import PasswordChangeDoneView, PasswordChangeView
from django.http import JsonResponse
from django.utils.cache import patch_cache_control, patch_vary_headers
from django.utils.decorators import method_decorator
from django.utils.translation import gettext, ngettext
from django.views.decorators.csrf import ensure_csrf_cookie
from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import PermissionDenied
from rest_framework.parsers import FormParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.views import APIView

from usuarios.web_api_views import WebSessionSchema
from usuarios.web_session import resolve_web_access


class PasswordChangeFieldSerializer(serializers.Serializer):
    name = serializers.ChoiceField(
        choices=["old_password", "new_password1", "new_password2"]
    )
    label = serializers.CharField()
    help_text = serializers.CharField(allow_blank=True)
    required = serializers.BooleanField()
    attrs = serializers.JSONField()


class PasswordChangeMetadataSerializer(serializers.Serializer):
    title = serializers.CharField()
    done_title = serializers.CharField()
    done_text = serializers.CharField()
    intro_text = serializers.CharField()
    submit_label = serializers.CharField()
    fields = PasswordChangeFieldSerializer(many=True)


class PasswordChangeRequestSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True, trim_whitespace=False)
    new_password1 = serializers.CharField(write_only=True, trim_whitespace=False)
    new_password2 = serializers.CharField(write_only=True, trim_whitespace=False)


class PasswordChangeResultSerializer(serializers.Serializer):
    ok = serializers.BooleanField(required=False)
    redirect = serializers.CharField(required=False)
    errors = serializers.JSONField(required=False)
    error_note = serializers.CharField(required=False)
    detail = serializers.CharField(required=False)
    state = serializers.CharField(required=False)
    required_action_url = serializers.CharField(required=False, allow_null=True)


class _PasswordChangeJSONView(PasswordChangeView):
    """Change rendering only; inherited form_valid owns save/session ordering."""

    def render_to_response(self, context, **response_kwargs):
        form = context["form"]
        fields = []
        for name, field in form.fields.items():
            bound = form[name]
            attrs = {
                **field.widget.attrs,
                **bound.build_widget_attrs({}, field.widget),
                "id": bound.id_for_label,
            }
            fields.append(
                {
                    "name": name,
                    "label": str(field.label),
                    "help_text": str(field.help_text),
                    "required": field.required,
                    "attrs": {
                        key: attrs[key]
                        for key in (
                            "id",
                            "autocomplete",
                            "autofocus",
                            "aria-describedby",
                        )
                        if key in attrs
                    },
                }
            )
        payload = {
            "title": str(context["title"]),
            "done_title": str(PasswordChangeDoneView.title),
            "done_text": gettext("Your password was changed."),
            "intro_text": gettext(
                "Please enter your old password, for security’s sake, and then enter "
                "your new password twice so we can verify you typed it in correctly."
            ),
            "submit_label": gettext("Change password"),
            "fields": fields,
        }
        return JsonResponse(PasswordChangeMetadataSerializer(payload).data)

    def form_invalid(self, form):
        return JsonResponse(
            {
                "errors": form.errors.get_json_data(),
                "error_note": ngettext(
                    "Please correct the error below.",
                    "Please correct the errors below.",
                    len(form.errors),
                ),
            },
            status=400,
        )


@method_decorator(ensure_csrf_cookie, name="dispatch")
class WebPasswordChangeView(APIView):
    """Require the same ready session on both local form and done pages."""

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
        if self.access.state != "ready":
            raise PermissionDenied("La sesión no permite cambiar la contraseña.")

    def get_authenticate_header(self, request):
        return "Session"

    def handle_exception(self, exc):
        response = super().handle_exception(exc)
        if self.access is not None and self.access.state != "ready":
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
    def source_response(request):
        # Django's sensitive-parameter/CSRF decorators require the real HttpRequest.
        # FormParser synchronizes form data onto that same framework-owned request.
        return _PasswordChangeJSONView.as_view()(
            request._request  # pylint: disable=protected-access
        )

    @extend_schema(
        responses={
            200: PasswordChangeMetadataSerializer,
            401: PasswordChangeResultSerializer,
            403: PasswordChangeResultSerializer,
        }
    )
    def get(self, request):
        return self.source_response(request)

    @extend_schema(
        request=PasswordChangeRequestSerializer,
        responses={
            200: PasswordChangeResultSerializer,
            400: PasswordChangeResultSerializer,
            401: PasswordChangeResultSerializer,
            403: PasswordChangeResultSerializer,
            405: PasswordChangeResultSerializer,
            415: PasswordChangeResultSerializer,
        },
    )
    def post(self, request):
        # Evaluate FormParser even for an empty body; JSON is never a mutation format.
        _ = request.data
        response = self.source_response(request)
        if response.status_code in (301, 302, 303):
            converted = Response({"ok": True, "redirect": response["Location"]})
            converted.cookies = response.cookies
            return converted
        return response
