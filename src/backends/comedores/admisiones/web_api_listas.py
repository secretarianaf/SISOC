"""Web API (G1 v1) of the admisiones technical and legal lists (AD03.01).

``GET /api/web/comedores/admisiones/tecnicos/`` and ``.../legales/`` run the
native ``AdmisionesTecnicosListView`` and ``AdmisionesLegalesListView`` themselves
(``setup()``, scoped queryset, filters, ordering, column preferences, pagination
and context), so they cannot drift from the HTML pages; this module only projects
that context to JSON. The access is exactly the native one: the URL guard
``permissions_any_required`` (the technical list accepts ``comedores.view_comedor``,
``admisiones.view_admision`` or ``acompanamientos.view_informacionrelevante``; the
legal list adds ``expedientespagos.view_expedientepago``), superuser bypass
included, and the per-actor scope of the native services. The list pages are
read-only; every action keeps navigating to the native URLs.
"""

import re

from django.http import Http404
from django.urls import reverse
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import NotFound
from rest_framework.permissions import BasePermission
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.views import APIView

# The exact predicate of ``permissions_any_required``, the native URL guard.
from core.decorators import _has_any_permissions
from core.pagination import build_compact_page_range
from core.web_gate import WebGatePermission
from admisiones.views.web_views import (
    AdmisionesLegalesListView,
    AdmisionesTecnicosListView,
)
from admisiones.web_api_templates import _native, pending_messages

TECNICOS_PERMISSIONS = [
    "comedores.view_comedor",
    "admisiones.view_admision",
    "acompanamientos.view_informacionrelevante",
]
LEGALES_PERMISSIONS = TECNICOS_PERMISSIONS + ["expedientespagos.view_expedientepago"]
BADGE = re.compile(r"<span[^>]*>([^<]+)</span>")


class VerTecnicos(BasePermission):
    """The native ``permissions_any_required`` of ``admisiones_tecnicos_listar``."""

    def has_permission(self, request, view):
        return _has_any_permissions(request.user, TECNICOS_PERMISSIONS)


class VerLegales(BasePermission):
    """The native ``permissions_any_required`` of ``admisiones_legales_listar``."""

    def has_permission(self, request, view):
        return _has_any_permissions(request.user, LEGALES_PERMISSIONS)


def _header(header):
    payload = {"title": str(header["title"]), "sort_url": None, "sort_direction": None}
    if header.get("sort_url"):
        payload["sort_url"] = header["sort_url"]
        payload["sort_direction"] = header.get("sort_direction")
    return payload


def _cell(cell):
    return {
        "content": str(cell["content"]),
        "data_attr": cell.get("data_attr"),
        "data_value": cell.get("data_value"),
        "link_url": cell.get("link_url"),
        "link_class": cell.get("link_class"),
        "link_title": cell.get("link_title"),
    }


def _action(action):
    """The native label is ``"Ver"`` plus a ``<span class="badge ...">`` markup: data here."""
    encontrado = BADGE.search(str(action["label"]))
    return {
        "label": "Ver" if encontrado else str(action["label"]),
        "badge": encontrado.group(1) if encontrado else None,
        "url": action["url"],
        "type": action["type"],
    }


def _query_prefix(request):
    """Link prefix of ``components/pagination.html``."""
    from django.utils.http import urlencode

    pares = [(k, v) for k, v in request.GET.items() if k != "page"]
    return urlencode(pares) + "&" if pares else ""


def _crumb(item):
    """``breadcrumb.html`` reads ``item.text``, which these items do not define.

    The native page therefore draws an empty text and, for the first item, an
    empty link whose ``href`` is the raw URL name. Both are kept as they are.
    """
    active = bool(item.get("active"))
    return {
        "text": str(item.get("text", "")),
        "url": None if active or not item.get("url") else item["url"],
        "active": active,
    }


class _ListaWebView(APIView):
    authentication_classes = [SessionAuthentication]
    renderer_classes = [JSONRenderer]
    http_method_names = ["get", "head"]
    view_class = None
    list_route = ""

    def get(self, request):
        vista = _native(self.view_class, request)
        try:
            vista.object_list = vista.get_queryset()
            context = vista.get_context_data()
        except Http404 as exc:
            raise NotFound() from exc
        page = context["page_obj"]
        return Response(
            {
                "title": context["titulo_busqueda"],
                "breadcrumb": [_crumb(item) for item in context["breadcrumb_items"]],
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
                },
                "columns": context["column_config"],
                "headers": [_header(h) for h in context["table_headers"]],
                "results": [
                    {
                        "cells": [_cell(cell) for cell in item["cells"]],
                        "actions": [_action(a) for a in item["actions"]],
                    }
                    for item in context["table_items"]
                ],
                "page": {
                    "is_paginated": context["is_paginated"],
                    "number": page.number,
                    "count": page.paginator.count,
                    "has_rows": len(page.object_list) > 0,
                    "previous": (
                        page.previous_page_number() if page.has_previous() else None
                    ),
                    "next": page.next_page_number() if page.has_next() else None,
                    "range": [
                        "…" if numero in ("...", "…") else numero
                        for numero in build_compact_page_range(page)
                    ],
                    "query_without_page": _query_prefix(request),
                },
                "messages": pending_messages(request),
            }
        )


class TecnicosListaWebView(_ListaWebView):
    """``GET /api/web/comedores/admisiones/tecnicos/``."""

    permission_classes = [WebGatePermission, VerTecnicos]
    view_class = AdmisionesTecnicosListView


class LegalesListaWebView(_ListaWebView):
    """``GET /api/web/comedores/admisiones/legales/``."""

    permission_classes = [WebGatePermission, VerLegales]
    view_class = AdmisionesLegalesListView
