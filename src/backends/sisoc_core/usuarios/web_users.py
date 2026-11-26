"""Session transport over the native user list and its activate/deactivate steps.

The native views stay the only owners of the queryset, the actor scope, the
filters, the column preferences and the state change: this module runs their
``get_queryset()``/``get_context_data()``/``post()`` and projects the result.
Nothing here widens who can list or manage a user.
"""

from django.contrib import messages
from django.http import JsonResponse
from django.template import Context
from django.template.base import render_value_in_context
from django.template.defaultfilters import urlencode
from django.urls import reverse
from django.utils.cache import patch_cache_control, patch_vary_headers
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie

from core.decorators import _has_any_permissions
from core.pagination import build_compact_page_range
from core.templatetags.custom_filters import has_any_perm
from usuarios.views import UserActiveView, UserDeleteView, UserListView
from usuarios.web_context import build_legacy_presentation
from usuarios.web_session import resolve_web_access

_LEVELS = {
    messages.ERROR: "error",
    messages.WARNING: "warning",
    messages.SUCCESS: "success",
}
EXPORT_BUTTON_PERMISSIONS = "auth.role_exportar_a_csv"


def pending_messages(request):
    """Consume queued Django messages exactly as the native page would."""
    return [
        {"message": str(message), "level": _LEVELS.get(message.level, "info")}
        for message in messages.get_messages(request)
    ]


def render_cell(value):
    """``{{ cell.content }}`` of ``data_table.html``: same localization, no escaping."""
    return render_value_in_context(value, Context(autoescape=False))


class _UserTransportMixin:
    """Prerequisites and the native URL guard plus view guard, before any lookup."""

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
        elif not (
            _has_any_permissions(request.user, self.required_permissions)
            and self.test_func()
        ):
            response = JsonResponse(
                {"detail": "No tiene permisos para esta acción."}, status=403
            )
        elif request.method.lower() not in self.http_method_names:
            response = self.http_method_not_allowed(request, *args, **kwargs)
        elif (
            request.method == "POST"
            and int(request.META.get("CONTENT_LENGTH") or 0)
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


def _can_export(user):
    return bool(user.is_superuser or has_any_perm(user, EXPORT_BUTTON_PERMISSIONS))


@method_decorator(ensure_csrf_cookie, name="dispatch")
@method_decorator(csrf_protect, name="dispatch")
class WebUserListView(_UserTransportMixin, UserListView):
    """The native list, filters, pagination and per-user column preferences."""

    http_method_names = ["get", "head", "options"]

    def render_to_response(self, context, **response_kwargs):
        page = context["page_obj"]
        return JsonResponse(
            {
                "filters_config": context["filters_config"],
                "favorites": {
                    "section": context["seccion_filtros_favoritos"],
                    "url": reverse("filtros_favoritos"),
                    "detail_url_template": reverse(
                        "detalle_filtro_favorito", kwargs={"pk": 0}
                    ),
                },
                "urls": {
                    "list": context["filters_action"],
                    "reset": context["reset_url"],
                    "add": context["add_url"],
                    "export": reverse("usuarios_exportar"),
                },
                "show_add_button": bool(context["show_add_button"]),
                "additional_buttons": [
                    {
                        "label": button["label"],
                        "url": button["url"],
                        "class": button["class"],
                        "title": button["title"],
                    }
                    for button in context["additional_buttons"]
                ],
                "can_export": _can_export(self.request.user),
                "columns": context["column_config"],
                "headers": [
                    {
                        "title": str(header["title"]),
                        "width": header.get("width") or "",
                        "sortable": bool(header.get("sortable")),
                        "sort_key": header.get("sort_key") or header["title"],
                    }
                    for header in context["table_headers"]
                ],
                "results": [
                    {
                        "id": user.pk,
                        "cells": [
                            render_cell(cell["content"]) for cell in item["cells"]
                        ],
                        "actions": [
                            {
                                "label": action["label"],
                                "url": action["url"],
                                "type": action["type"],
                                "icon": action["icon"],
                            }
                            for action in item["actions"]
                        ],
                    }
                    for user, item in zip(context["users"], context["user_table_items"])
                ],
                "page": {
                    "is_paginated": context["is_paginated"],
                    "number": page.number,
                    "count": page.paginator.count,
                    "previous": (
                        page.previous_page_number() if page.has_previous() else None
                    ),
                    "next": page.next_page_number() if page.has_next() else None,
                    "range": [
                        "…" if number in ("...", "…") else number
                        for number in build_compact_page_range(page)
                    ],
                    "query_without_page": "".join(
                        f"{key}={urlencode(value)}&"
                        for key, value in self.request.GET.items()
                        if key not in ("page", "busqueda")
                    ),
                },
                "messages": pending_messages(self.request),
                "presentation": build_legacy_presentation(self.request),
            }
        )


class _StateTransportMixin(_UserTransportMixin):
    """Confirm step: GET names the user, POST is the native state change."""

    title = ""
    confirm_text = ""
    confirm_class = ""
    message = ""

    def render_to_response(self, context, **response_kwargs):
        return JsonResponse(
            {
                "title": self.title,
                "message": self.message,
                "object_name": self.object.username.upper(),
                "confirm_text": self.confirm_text,
                "confirm_class": self.confirm_class,
                "cancel_url": reverse("usuarios"),
                "presentation": build_legacy_presentation(self.request),
            }
        )


@method_decorator(ensure_csrf_cookie, name="dispatch")
@method_decorator(csrf_protect, name="dispatch")
class WebUserDeactivateView(_StateTransportMixin, UserDeleteView):
    """Native deactivation inside the actor scope: ``is_active=False`` only."""

    title = "Desactivar Usuario"
    confirm_text = "Desactivar"
    confirm_class = "btn-danger"
    message = "¿Estás seguro que deseas desactivar el usuario"


@method_decorator(ensure_csrf_cookie, name="dispatch")
@method_decorator(csrf_protect, name="dispatch")
class WebUserActivateView(_StateTransportMixin, UserActiveView):
    """Native activation inside the actor scope: ``is_active=True`` only."""

    title = "Activar Usuario"
    confirm_text = "Activar"
    confirm_class = "btn-success"
    message = "¿Estás seguro que deseas activar el usuario"
