"""Public session-login transport; authentication stays in Django's LoginView."""

from django.http import JsonResponse
from django.utils.cache import patch_cache_control, patch_vary_headers
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie

from core.context_processors import footer_version
from users.profile_utils import get_profile_or_none
from usuarios.auth_views import UsuariosLoginView


@method_decorator(ensure_csrf_cookie, name="dispatch")
@method_decorator(csrf_protect, name="dispatch")
class WebLoginView(UsuariosLoginView):
    """Expose the existing Form/session effects without a PWA token contract."""

    http_method_names = ["get", "head", "post", "options"]

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and not getattr(
            get_profile_or_none(request.user), "acceso_web", False
        ):
            response = JsonResponse(
                {"detail": "Este usuario no tiene acceso SISOC web habilitado."},
                status=403,
            )
        elif request.method.lower() not in self.http_method_names:
            response = self.http_method_not_allowed(request, *args, **kwargs)
        elif (
            request.method == "POST"
            and request.content_type != "application/x-www-form-urlencoded"
        ):
            response = JsonResponse(
                {"detail": "Formato de solicitud no admitido."}, status=415
            )
        else:
            # Inherited dispatch enforces anonymous CSRF, authenticates through
            # BackofficeAuthenticationForm and validates redirect destinations.
            response = super().dispatch(request, *args, **kwargs)
            if response.status_code in (301, 302, 303):
                converted = JsonResponse({"ok": True, "redirect": response["Location"]})
                # csrf_protect may already have installed the rotated cookie.
                # Replacing the response must preserve its attributes and value.
                converted.cookies = response.cookies
                response = converted
        patch_cache_control(response, private=True, no_store=True)
        patch_vary_headers(response, ("Cookie",))
        return response

    def render_to_response(self, context, **response_kwargs):
        form = context["form"]
        return JsonResponse(
            {
                "fields": [
                    {
                        "name": name,
                        "label": str(form.fields[name].label),
                        "required": form.fields[name].required,
                        "max_length": form.fields[name].max_length,
                    }
                    for name in ("username", "password")
                ],
                "initial": {"username": ""},
                "errors": {},
                "footer_version_label": footer_version(self.request)[
                    "footer_version_label"
                ],
            }
        )

    def form_invalid(self, form):
        return JsonResponse(
            {
                "errors": form.errors.get_json_data(),
                "initial": {"username": form.data.get("username", "")},
            },
            status=400,
        )
