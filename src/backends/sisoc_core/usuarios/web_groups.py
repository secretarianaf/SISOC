"""Session transport over native group Forms, permissions and view hooks."""

from django.contrib import messages
from django.http import JsonResponse
from django.utils.cache import patch_cache_control, patch_vary_headers
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie

from usuarios.views import GroupCreateView, GroupListView, GroupUpdateView
from usuarios.web_context import build_legacy_presentation
from usuarios.web_session import resolve_web_access


class _GroupTransportMixin:
    """Keep business prerequisites and action permissions ahead of object access."""

    http_method_names = ["get", "head", "post", "options"]

    def dispatch(self, request, *args, **kwargs):
        access = resolve_web_access(request)
        if access.state != "ready":
            response = JsonResponse(
                {
                    "detail": "Debe completar el requisito de acceso correspondiente.",
                    "state": access.state,
                    "required_action_url": access.required_action_url,
                },
                status=401 if access.state == "unauthenticated" else 403,
            )
        elif not request.user.has_perms(self.required_permissions):
            response = JsonResponse(
                {"detail": "No tiene permisos para esta acción."}, status=403
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
            if response.status_code == 302:
                converted = JsonResponse({"ok": True, "redirect": response["Location"]})
                converted.cookies = response.cookies
                response = converted
        patch_cache_control(response, private=True, no_store=True)
        patch_vary_headers(response, ("Cookie",))
        return response


class _GroupFormTransportMixin(_GroupTransportMixin):
    """Serialize only the fields already available to native group editors."""

    def form_invalid(self, form):
        return self.render_to_response(self.get_context_data(form=form), status=400)

    def render_to_response(self, context, **response_kwargs):
        form = context["form"]
        name = form.fields["name"]
        permissions = form.fields["permissions"]
        return JsonResponse(
            {
                "title": context["form_title"],
                "submit_text": context["submit_text"],
                "fields": [
                    {
                        "name": "name",
                        "label": str(name.label),
                        "required": name.required,
                        "max_length": name.max_length,
                        "help_text": str(name.help_text),
                    },
                    {
                        "name": "permissions",
                        "label": str(permissions.label),
                        "required": permissions.required,
                        "help_text": str(permissions.help_text),
                        "choices": [
                            {
                                "id": item.pk,
                                "label": permissions.label_from_instance(item),
                            }
                            for item in permissions.queryset
                        ],
                    },
                ],
                "initial": {
                    "name": form["name"].value() or "",
                    "permissions": [
                        str(value) for value in (form["permissions"].value() or [])
                    ],
                },
                "errors": form.errors.get_json_data() if form.is_bound else {},
                "presentation": build_legacy_presentation(self.request),
            },
            status=response_kwargs.get("status", 200),
        )


@method_decorator(ensure_csrf_cookie, name="dispatch")
@method_decorator(csrf_protect, name="dispatch")
class WebGroupListView(_GroupTransportMixin, GroupListView):
    """Read the same filtered list and per-user column preferences as HTML."""

    http_method_names = ["get", "head", "options"]

    def render_to_response(self, context, **response_kwargs):
        levels = {
            messages.ERROR: "error",
            messages.WARNING: "warning",
            messages.SUCCESS: "success",
        }
        return JsonResponse(
            {
                "items": [
                    {
                        "id": group.pk,
                        "name": group.name,
                        "permissions_count": group.permissions_count,
                    }
                    for group in context["groups"]
                ],
                "query": context["query"],
                "columns": context["column_config"],
                "can_export": self.request.user.is_superuser
                or self.request.user.has_perm("auth.role_exportar_a_csv"),
                "messages": [
                    {
                        "message": str(message),
                        "level": levels.get(message.level, "info"),
                    }
                    for message in messages.get_messages(self.request)
                ],
                "presentation": build_legacy_presentation(self.request),
            }
        )


@method_decorator(ensure_csrf_cookie, name="dispatch")
@method_decorator(csrf_protect, name="dispatch")
class WebGroupCreateView(_GroupFormTransportMixin, GroupCreateView):
    """Save through the original GroupForm and success-message hook."""


@method_decorator(ensure_csrf_cookie, name="dispatch")
@method_decorator(csrf_protect, name="dispatch")
class WebGroupUpdateView(_GroupFormTransportMixin, GroupUpdateView):
    """Reuse original object lookup and permission propagation through GroupForm."""
