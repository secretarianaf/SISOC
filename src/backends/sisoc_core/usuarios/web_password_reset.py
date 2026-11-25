"""Public session JSON transport over the unchanged password-recovery views.

Email delivery, account matching and the token-to-session exchange stay in the
source views. The confirmation endpoint never receives a reset token: it only
reads the session token stored by the source ``/reset/<uidb64>/<token>/`` GET.
"""

from django.http import JsonResponse
from django.utils.cache import patch_cache_control, patch_vary_headers
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie

from core.context_processors import footer_version
from usuarios.auth_views import PasswordResetConfirmCustomView, SisocPasswordResetView

_ATTRS = ("id", "autocomplete", "maxlength", "aria-describedby")


def _field_metadata(form, name):
    field = form.fields[name]
    bound = form[name]
    attrs = {
        **field.widget.attrs,
        **bound.build_widget_attrs({}, field.widget),
        "id": bound.id_for_label,
    }
    return {
        "name": name,
        "label": str(field.label),
        "required": field.required,
        "attrs": {key: str(attrs[key]) for key in _ATTRS if key in attrs},
    }


class _PublicJSONMixin:
    """Shared transport rules of the public login API, applied to recovery."""

    http_method_names = ["get", "head", "post", "options"]

    def dispatch(self, request, *args, **kwargs):
        if request.method.lower() not in self.http_method_names:
            response = self.http_method_not_allowed(request, *args, **kwargs)
        elif (
            request.method == "POST"
            and request.content_type != "application/x-www-form-urlencoded"
        ):
            response = JsonResponse(
                {"detail": "Formato de solicitud no admitido."}, status=415
            )
        else:
            response = super().dispatch(request, *args, **kwargs)
            if response.status_code in (301, 302, 303):
                converted = JsonResponse({"ok": True, "redirect": response["Location"]})
                converted.cookies = response.cookies
                response = converted
        patch_cache_control(response, private=True, no_store=True)
        patch_vary_headers(response, ("Cookie",))
        return response


@method_decorator(ensure_csrf_cookie, name="dispatch")
@method_decorator(csrf_protect, name="dispatch")
class WebPasswordResetView(_PublicJSONMixin, SisocPasswordResetView):
    """Same form, matching and existing mail send; one done for every request."""

    def render_to_response(self, context, **response_kwargs):
        form = context["form"]
        fields = []
        for name in ("username", "email"):
            metadata = _field_metadata(form, name)
            metadata["type"] = form.fields[name].widget.input_type
            fields.append(
                {
                    key: metadata[key]
                    for key in ("name", "label", "type", "required", "attrs")
                }
            )
        return JsonResponse(
            {
                "fields": fields,
                "footer_version_label": footer_version(self.request)[
                    "footer_version_label"
                ],
            }
        )

    def form_invalid(self, form):
        return JsonResponse({"errors": form.errors.get_json_data()}, status=400)


@method_decorator(ensure_csrf_cookie, name="dispatch")
@method_decorator(csrf_protect, name="dispatch")
class WebPasswordResetConfirmView(_PublicJSONMixin, PasswordResetConfirmCustomView):
    """Revalidate the source session exchange on every GET and POST."""

    def dispatch(self, request, *args, **kwargs):
        # Only the session token written by the source GET can authorize a reset.
        kwargs["token"] = self.reset_url_token
        return super().dispatch(request, *args, **kwargs)

    def render_to_response(self, context, **response_kwargs):
        if not context.get("validlink"):
            return JsonResponse({"validlink": False})
        form = context["form"]
        fields = []
        for name in ("new_password1", "new_password2"):
            metadata = _field_metadata(form, name)
            metadata["help_text"] = str(form.fields[name].help_text or "")
            fields.append(metadata)
        return JsonResponse({"validlink": True, "fields": fields})

    def form_invalid(self, form):
        return JsonResponse(
            {"validlink": True, "errors": form.errors.get_json_data()}, status=400
        )
