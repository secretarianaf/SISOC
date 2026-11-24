"""Web API (G1 v1) of the global list of monthly rendiciones (RM01.01).

``/api/web/comedores/`` is published by the Comedores backend (``url_prefixes``
in ``src/backends/config/backends.json``). In a split deploy the core checks the
session and the web prerequisites and signs each request; the runtime only
serves requests its ``WebGateMiddleware`` verified. In the monolith
``WebGatePermission`` evaluates the same policy locally. After that the native
rule applies unchanged: superuser or any of the five codes of
``rendicioncuentasmensual/urls.py``, with no object scope (kept on purpose, see
``docs/registro/decisiones/2026-11-10-2785-brechas-acceso-conservadas.md``).

The endpoint runs ``RendicionCuentaMensualGlobalListView`` itself (queryset,
advanced filters, territorial and stage filters, column preferences, the
25-row paginator with its 404 and the context); this module only projects that
context to JSON. Each cell is rendered with the page's own include
(``components/rendicion_global_list_cell.html``), so React never formats dates,
periods or states. The CSV export stays the native GET ``listado/?export=csv``.
"""

from html.parser import HTMLParser

from django.contrib import messages
from django.http import Http404
from django.template.defaultfilters import urlencode
from django.template.loader import get_template
from django.urls import reverse
from django.utils.encoding import iri_to_uri
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import NotFound
from rest_framework.permissions import BasePermission
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.views import APIView

# The exact predicate of ``permissions_any_required``, the native URL guard.
from core.decorators import _has_any_permissions
from core.pagination import build_compact_page_range
from core.templatetags.custom_filters import has_any_perm
from core.web_gate import WebGatePermission
from rendicioncuentasmensual.urls import _RENDICION_ACCESS_PERMS
from rendicioncuentasmensual.views import RendicionCuentaMensualGlobalListView

# ``search_bar.html`` with ``export_url`` and its default permissions.
EXPORT_BUTTON_PERMISSIONS = "auth.role_exportar_a_csv"
# ``rendicioncuentasmensual_global_list.html``: ``perms.<app>.<codename>``.
NUEVA_AUDITORIA_PERMISSION = "rendicioncuentasmensual.manage_auditoria_stage"
CELL_TEMPLATE = "components/rendicion_global_list_cell.html"
MESSAGE_LEVELS = {
    messages.DEBUG: "info",
    messages.INFO: "info",
    messages.SUCCESS: "success",
    messages.WARNING: "warning",
    messages.ERROR: "error",
}


class RendicionAccess(BasePermission):
    """Same rule as the native ``permissions_any_required(_RENDICION_ACCESS_PERMS)``."""

    def has_permission(self, request, view):
        return _has_any_permissions(request.user, _RENDICION_ACCESS_PERMS)


class _Celda(HTMLParser):
    """Text (whitespace collapsed, as the browser shows it) and badge of a ``<td>``."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.partes = []
        self.badge = None

    def handle_starttag(self, tag, attrs):
        if tag == "span" and self.badge is None:
            self.badge = dict(attrs).get("class")

    def handle_data(self, data):
        self.partes.append(data)

    def celda(self):
        return {"text": " ".join("".join(self.partes).split()), "badge": self.badge}


def _celda(template, rendicion, column_key):
    parser = _Celda()
    parser.feed(template.render({"rendicion": rendicion, "column_key": column_key}))
    parser.close()
    return parser.celda()


def _breadcrumb(items):
    """``components/breadcrumb.html``: a link only when not active nor last."""
    ultimo = len(items) - 1
    return [
        {
            "text": str(item["text"]),
            "url": (
                str(item["url"])
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


def _export_url(request, listado):
    """The native ``export_url``: the page's full path plus ``export=csv``."""
    query = request.META.get("QUERY_STRING", "")
    ruta = f"{listado}?{iri_to_uri(query)}" if query else listado
    return f"{ruta}{'&' if '?' in ruta else '?'}export=csv"


def _pending_messages(request):
    """Consume queued Django messages exactly as the native page would."""
    return [
        {"message": str(m), "level": MESSAGE_LEVELS.get(m.level, "info")}
        for m in messages.get_messages(request)
    ]


class RendicionListadoWebView(APIView):
    """``GET .../rendicioncuentasmensual/listado/``: ``rendicioncuentasmensual_global_list.html``."""

    authentication_classes = [SessionAuthentication]
    permission_classes = [WebGatePermission, RendicionAccess]
    renderer_classes = [JSONRenderer]
    http_method_names = ["get", "head"]

    def get(self, request):
        vista = RendicionCuentaMensualGlobalListView()
        vista.setup(request._request)  # pylint: disable=protected-access
        try:
            vista.object_list = vista.get_queryset()
            context = vista.get_context_data()
        except Http404 as exc:
            raise NotFound() from exc
        user = request.user
        listado = reverse("rendicioncuentasmensual_global_list")
        celda = get_template(CELL_TEMPLATE)
        activas = context["active_columns"]
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
                    "reset": reverse(context["reset_url"]),
                    "export": _export_url(request, listado),
                    "nueva_auditoria": reverse(
                        "rendicioncuentasmensual_auditoria_nueva"
                    ),
                },
                "can_export": user.is_superuser
                or has_any_perm(user, EXPORT_BUTTON_PERMISSIONS),
                "can_nueva_auditoria": user.has_perm(NUEVA_AUDITORIA_PERMISSION),
                "columns": context["column_config"],
                "headers": [
                    str(header["title"]) for header in context["table_headers"]
                ],
                "results": [
                    {
                        "id": rendicion.pk,
                        "cells": [_celda(celda, rendicion, key) for key in activas],
                        "detail_url": reverse(
                            "rendicioncuentasmensual_detail", args=[rendicion.pk]
                        ),
                    }
                    for rendicion in context["rendiciones_cuentas_mensuales"]
                ],
                "page": _pagina(context, request),
                "messages": _pending_messages(request),
            }
        )
