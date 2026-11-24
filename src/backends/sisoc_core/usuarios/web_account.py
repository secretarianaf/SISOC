"""Own-account JSON transport over the unchanged HTML Form and view hooks."""

from django.contrib import messages
from django.http import JsonResponse
from django.utils.cache import patch_cache_control, patch_vary_headers
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie

from usuarios.auth_views import ConfirmacionDatosView, MiCuentaView
from usuarios.web_context import build_legacy_presentation
from usuarios.web_session import resolve_web_access


class _AccountTransportMixin:
    """Keep current-user ownership and atomic saving in MiCuentaView/MiCuentaForm."""

    http_method_names = ["get", "head", "post", "options"]
    confirmation = False
    saved = False

    def dispatch(self, request, *args, **kwargs):
        access = resolve_web_access(request)
        allowed = {"ready"}
        if self.confirmation:
            # The original confirmation URL is survey-exempt and already-confirmed
            # dispatch redirects without writing, even with a pending survey.
            allowed |= {"profile_confirmation_required", "mandatory_survey_required"}
        if access.state not in allowed:
            response = JsonResponse(
                {
                    "detail": "Debe completar el requisito de acceso correspondiente.",
                    "state": access.state,
                    "required_action_url": access.required_action_url,
                },
                status=401 if access.state == "unauthenticated" else 403,
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
            response = super().dispatch(request, *args, **kwargs)
            if response.status_code in (301, 302, 303):
                payload = {"ok": True, "redirect": response["Location"]}
                if self.saved:
                    payload["message"] = "Datos personales actualizados correctamente."
                converted = JsonResponse(payload)
                converted.cookies = response.cookies
                response = converted
        patch_cache_control(response, private=True, no_store=True)
        patch_vary_headers(response, ("Cookie",))
        return response

    def form_valid(self, form):
        response = super().form_valid(form)
        self.saved = True
        return response

    def form_invalid(self, form):
        return self.form_response(form, status=400)

    def render_to_response(self, context, **response_kwargs):
        return self.form_response(context["form"])

    def form_response(self, form, status=200):
        payload = {
            "fields": [
                {
                    "name": name,
                    "label": str(field.label),
                    "help_text": str(field.help_text),
                    "required": field.required,
                    "max_length": getattr(field, "max_length", None),
                    "input_type": field.widget.input_type,
                }
                for name, field in form.fields.items()
            ],
            "initial": {name: form[name].value() or "" for name in form.fields},
            "errors": form.errors.get_json_data() if form.is_bound else {},
            "presentation": build_legacy_presentation(self.request),
        }
        if self.request.method in {"GET", "HEAD"}:
            levels = {
                messages.ERROR: "error",
                messages.WARNING: "warning",
                messages.SUCCESS: "success",
            }
            payload["messages"] = [
                {"message": str(message), "level": levels.get(message.level, "info")}
                for message in messages.get_messages(self.request)
            ]
        return JsonResponse(payload, status=status)


@method_decorator(ensure_csrf_cookie, name="dispatch")
@method_decorator(csrf_protect, name="dispatch")
class WebAccountView(_AccountTransportMixin, MiCuentaView):
    """Edit only the current session user's authorized six fields."""


@method_decorator(ensure_csrf_cookie, name="dispatch")
@method_decorator(csrf_protect, name="dispatch")
class WebAccountConfirmationView(_AccountTransportMixin, ConfirmacionDatosView):
    """Resolve only the profile prerequisite without requiring business readiness."""

    confirmation = True
