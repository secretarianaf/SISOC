"""Web API (G1 v1) of the Duplas screens (equipo técnico) for React.

``/api/web/comedores/`` is published by the comedores backend (``url_prefixes``
in ``src/backends/config/backends.json``). In a split deploy the core checks the
session and the web prerequisites and signs each request; the runtime only
serves requests its ``WebGateMiddleware`` verified. In the monolith
``WebGatePermission`` evaluates the same policy locally. After that the native
rule applies unchanged: ``auth.role_admin`` through the same check as
``permissions_any_required`` (superuser bypass included).

Each endpoint runs the native view itself (``setup()``, queryset, filters,
column preferences, pagination and context), so it cannot drift from the
HTML page; this module only projects that context to JSON. The CSV export
stays the native GET ``/equipo-tecnico/exportar/``. Read-only: GET only.
"""

from django.contrib import messages
from django.http import Http404
from django.template.defaultfilters import date as date_filter
from django.template.defaultfilters import urlencode
from django.urls import reverse
from django.utils import timezone
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import NotFound
from rest_framework.permissions import BasePermission
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.views import APIView

# The exact predicate of ``permissions_any_required``, the native URL guard.
from core.decorators import _has_any_permissions
from core.pagination import build_compact_page_range
from core.templatetags.custom_filters import has_any_perm, safe_getattr
from core.web_gate import WebGatePermission
from duplas.views import DuplaDetailView, DuplaListView

ADMIN_PERMISSIONS = ["auth.role_admin"]
# ``search_bar.html`` default ``export_permissions``; the URL itself also
# accepts ``auth.role_admin`` (``duplas/urls.py``), the button does not.
EXPORT_BUTTON_PERMISSIONS = "auth.role_exportar_a_csv"
MESSAGE_LEVELS = {
    messages.DEBUG: "info",
    messages.INFO: "info",
    messages.SUCCESS: "success",
    messages.WARNING: "warning",
    messages.ERROR: "error",
}


class RoleAdmin(BasePermission):
    """Same rule as the native ``permissions_any_required(["auth.role_admin"])``."""

    def has_permission(self, request, view):
        return _has_any_permissions(request.user, ADMIN_PERMISSIONS)


class DuplasWebView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [WebGatePermission, RoleAdmin]
    renderer_classes = [JSONRenderer]


def pending_messages(request):
    """Consume queued Django messages exactly as the native page would."""
    return [
        {
            "message": str(message),
            "level": MESSAGE_LEVELS.get(message.level, "info"),
        }
        for message in messages.get_messages(request)
    ]


def native_view(view_class, request, **kwargs):
    view = view_class()
    view.setup(request._request, **kwargs)  # pylint: disable=protected-access
    return view


def _breadcrumb(items):
    """``components/breadcrumb.html``: a link only when not active nor last."""
    ultimo = len(items) - 1
    return [
        {
            "text": item["text"],
            "url": (
                item["url"]
                if item.get("url") and not item.get("active") and indice != ultimo
                else None
            ),
        }
        for indice, item in enumerate(items)
    ]


def _query_without_page(request):
    """Prefix of ``components/pagination.html`` links (``busqueda`` dropped)."""
    return "".join(
        f"{clave}={urlencode(valor)}&"
        for clave, valor in request.GET.items()
        if clave not in ("page", "busqueda")
    )


def _pagina(context, request):
    page = context["page_obj"]
    return {
        "is_paginated": context["is_paginated"],
        "number": page.number,
        "count": page.paginator.count,
        "previous": page.previous_page_number() if page.has_previous() else None,
        "next": page.next_page_number() if page.has_next() else None,
        "range": [
            "…" if numero in ("...", "…") else numero
            for numero in build_compact_page_range(page)
        ],
        "query_without_page": _query_without_page(request),
    }


def _fila(dupla, fields, actions):
    return {
        "id": dupla.pk,
        "cells": [safe_getattr(dupla, field["name"]) for field in fields],
        "actions": [
            {
                "label": action["label"],
                "url": reverse(action["url_name"], args=[dupla.pk]),
                "type": action["type"],
                "icon": action["icon"],
            }
            for action in actions
        ],
    }


class DuplaListWebView(DuplasWebView):
    """``GET /api/web/comedores/duplas/``: the native list with its filters."""

    http_method_names = ["get", "head"]

    def get(self, request):
        vista = native_view(DuplaListView, request)
        try:
            vista.object_list = vista.get_queryset()
            context = vista.get_context_data()
        except Http404 as exc:
            raise NotFound() from exc
        user = request.user
        fields = context["table_fields"]
        return Response(
            {
                "breadcrumb": _breadcrumb(context["breadcrumb_items"]),
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
                    "export": reverse("dupla_exportar"),
                },
                "can_export": user.is_superuser
                or has_any_perm(user, EXPORT_BUTTON_PERMISSIONS),
                "columns": context["column_config"],
                "headers": [
                    {
                        "title": str(header["title"]),
                        "sortable": bool(header.get("sortable")),
                        "sort_key": header.get("sort_key") or header["title"],
                    }
                    for header in context["table_headers"]
                ],
                "results": [
                    _fila(dupla, fields, context["table_actions"])
                    for dupla in context["duplas"]
                ],
                "page": _pagina(context, request),
                "messages": pending_messages(request),
            }
        )


def _nombre(user):
    """``user.get_full_name|default:user.username`` of ``dupla_detail.html``."""
    return user.get_full_name() or user.username


class DuplaDetailWebView(DuplasWebView):
    """``GET /api/web/comedores/duplas/<pk>/``: the native detail card."""

    http_method_names = ["get", "head"]

    def get(self, request, pk):
        vista = native_view(DuplaDetailView, request, pk=pk)
        try:
            dupla = vista.get_object()
        except Http404 as exc:
            raise NotFound() from exc
        return Response(
            {
                "id": dupla.pk,
                "nombre": dupla.nombre,
                "estado": dupla.estado,
                "tecnicos": dupla.tecnicos_nombres,
                "abogado": _nombre(dupla.abogado),
                "coordinador": (
                    _nombre(dupla.coordinador) if dupla.coordinador else None
                ),
                "fecha": date_filter(timezone.localtime(dupla.fecha), "d/m/Y H:i"),
                "urls": {
                    "list": reverse("dupla_list"),
                    "edit": reverse("dupla_editar", args=[dupla.pk]),
                    "delete": reverse("dupla_eliminar", args=[dupla.pk]),
                },
                "messages": pending_messages(request),
            }
        )
