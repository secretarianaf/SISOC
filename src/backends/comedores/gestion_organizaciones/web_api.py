"""Web API (G1 v1) of the Organizaciones list (O05.01).

``/api/web/comedores/`` is published by the Comedores backend (``url_prefixes``
in ``src/backends/config/backends.json``). In a split deploy the core checks the
session and the web prerequisites and signs each request; the runtime only
serves requests its ``WebGateMiddleware`` verified. In the monolith
``WebGatePermission`` evaluates the same policy locally. After that the native
rule applies unchanged: ``permissions_any_required`` with
``ORGANIZACION_DOCUMENTACION_PERMS`` and the dupla scope of the native list
(kept on purpose, see
``docs/registro/decisiones/2026-11-10-2785-brechas-acceso-conservadas.md``).

The endpoint runs ``OrganizacionListView`` itself (simple search, advanced
filters, ``-id`` order, the 10-row ``NoCountPaginator`` and the context) and
renders the page's own rows include
(``organizaciones/partials/organizacion_rows.html``), so React shows the same
text, the same ``data-*`` sort values of ``listSort.js`` and the same actions.
The CSV export stays the native GET ``/organizaciones/exportar``.
"""

from html.parser import HTMLParser

from django.contrib import messages
from django.template import RequestContext
from django.template.defaultfilters import urlencode
from django.template.loader import get_template, render_to_string
from django.template.loader_tags import BlockNode
from django.templatetags.static import static
from django.urls import reverse
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import BasePermission
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.views import APIView

# The exact predicate of ``permissions_any_required``, the native URL guard.
from core.decorators import _has_any_permissions
from core.pagination import build_compact_page_range
from core.templatetags.custom_filters import has_any_perm
from core.web_gate import WebGatePermission
from gestion_organizaciones.urls import ORGANIZACION_DOCUMENTACION_PERMS
from gestion_organizaciones.views import OrganizacionDetailView, OrganizacionListView

# ``search_bar.html`` with ``export_url`` and its default permissions.
EXPORT_BUTTON_PERMISSIONS = "auth.role_exportar_a_csv"
ROWS_TEMPLATE = "organizaciones/partials/organizacion_rows.html"
MESSAGE_LEVELS = {
    messages.DEBUG: "info",
    messages.INFO: "info",
    messages.SUCCESS: "success",
    messages.WARNING: "warning",
    messages.ERROR: "error",
}


class OrganizacionListAccess(BasePermission):
    """Same rule as ``permissions_any_required(ORGANIZACION_DOCUMENTACION_PERMS)``."""

    def has_permission(self, request, view):
        return _has_any_permissions(request.user, ORGANIZACION_DOCUMENTACION_PERMS)


class _Filas(HTMLParser):
    """Rows of ``organizacion_rows.html``: cell text, ``data-*`` value and links."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.rows = []
        self.empty = None
        self._celda = None
        self._link = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "tr":
            self.rows.append([])
        elif tag == "td":
            data = [(k[5:], v) for k, v in attrs.items() if k.startswith("data-")]
            self._celda = {
                "text": [],
                "sort": data[0][1] if data else None,
                "colspan": attrs.get("colspan"),
                "links": [],
            }
        elif tag == "a" and self._celda is not None:
            self._link = {
                "url": attrs.get("href"),
                "class": attrs.get("class") or "",
                "title": attrs.get("title") or "",
                "icon": None,
                "text": [],
            }
        elif tag == "i" and self._link is not None:
            self._link["icon"] = attrs.get("class")

    def handle_endtag(self, tag):
        if tag == "a" and self._link is not None:
            self._link["text"] = " ".join("".join(self._link["text"]).split())
            self._celda["links"].append(self._link)
            self._link = None
        elif tag == "td" and self._celda is not None:
            celda = self._celda
            celda["text"] = " ".join("".join(celda["text"]).split())
            if celda.pop("colspan"):
                self.empty = celda["text"]
                self.rows.pop()
            else:
                self.rows[-1].append(celda)
            self._celda = None

    def handle_data(self, data):
        if self._link is not None:
            self._link["text"].append(data)
        if self._celda is not None:
            self._celda["text"].append(data)


def _filas(request, organizaciones, puede_gestionar):
    parser = _Filas()
    parser.feed(
        render_to_string(
            ROWS_TEMPLATE,
            {
                "organizaciones": organizaciones,
                "puede_gestionar_organizaciones": puede_gestionar,
            },
            request=request,
        )
    )
    parser.close()
    resultados = []
    for organizacion, celdas in zip(organizaciones, parser.rows):
        *datos, acciones = celdas
        nombre = datos[1]["links"][0]
        resultados.append(
            {
                "id": organizacion.pk,
                "cells": [{"text": c["text"], "sort": c["sort"]} for c in datos],
                "detail_url": nombre["url"],
                "actions": [
                    {
                        "label": a["text"],
                        "url": a["url"],
                        "class": a["class"],
                        "title": a["title"],
                        "icon": a["icon"],
                    }
                    for a in acciones["links"]
                ],
            }
        )
    return resultados, parser.empty


def _query_prefix(request, query):
    """Prefix of ``components/pagination.html`` links with ``query=query``."""
    prefijo = f"busqueda={urlencode(query)}&" if query else ""
    return prefijo + "".join(
        f"{clave}={urlencode(valor)}&"
        for clave, valor in request.GET.items()
        if clave not in ("page", "busqueda")
    )


def _pagina(context, request):
    page = context["page_obj"]
    return {
        "is_paginated": context["is_paginated"],
        "number": page.number,
        "previous": page.previous_page_number() if page.has_previous() else None,
        "next": page.next_page_number() if page.has_next() else None,
        "range": [
            "…" if numero in ("...", "…") else numero
            # ``pagination.html``: ``page_range`` or ``page_obj|compact_page_range``.
            for numero in context.get("page_range") or build_compact_page_range(page)
        ],
        "query_prefix": _query_prefix(request, context["query"]),
    }


def _pending_messages(request):
    """Consume queued Django messages exactly as the native page would."""
    return [
        {"message": str(m), "level": MESSAGE_LEVELS.get(m.level, "info")}
        for m in messages.get_messages(request)
    ]


class OrganizacionListadoWebView(APIView):
    """``GET .../organizaciones/listado/``: ``organizacion_list.html``."""

    authentication_classes = [SessionAuthentication]
    permission_classes = [WebGatePermission, OrganizacionListAccess]
    renderer_classes = [JSONRenderer]
    http_method_names = ["get", "head"]

    def get(self, request):
        vista = OrganizacionListView()
        vista.setup(request._request)  # pylint: disable=protected-access
        vista.object_list = vista.get_queryset()
        context = vista.get_context_data()
        user = request.user
        resultados, vacio = _filas(
            request._request,  # pylint: disable=protected-access
            context["organizaciones"],
            context["puede_gestionar_organizaciones"],
        )
        listado = reverse("organizaciones")
        return Response(
            {
                "breadcrumb": [
                    {"text": "Organizaciones", "url": listado},
                    {"text": "Listar", "url": None},
                ],
                "filters_config": context["filters_config"],
                "favorites": {
                    "section": "",
                    "url": reverse("filtros_favoritos"),
                    "detail_url_template": reverse(
                        "detalle_filtro_favorito", kwargs={"pk": 0}
                    ),
                },
                "urls": {
                    "list": listado,
                    "reset": listado,
                    "add": reverse("organizacion_crear"),
                    "export": reverse("organizacion_exportar"),
                },
                "can_add": context["puede_crear_organizacion"],
                "can_export": user.is_superuser
                or has_any_perm(user, EXPORT_BUTTON_PERMISSIONS),
                "results": resultados,
                "empty": vacio,
                "page": _pagina(context, request._request),  # pylint: disable=W0212
                "messages": _pending_messages(request),
            }
        )


LEGAJO_TEMPLATE = "organizacion_detail.html"
LEGAJO_SCRIPTS = ("custom/js/organizacionesDocumentos.js",)


def _bloque(template, nombre):
    for nodo in template.template.nodelist.get_nodes_by_type(BlockNode):
        if nodo.name == nombre:
            return nodo
    raise LookupError(nombre)


class OrganizacionLegajoWebView(APIView):
    """``GET .../organizaciones/<pk>/``: ``organizacion_detail.html`` (legajo).

    Runs the native ``OrganizacionDetailView`` (dupla scope, program and section
    parameters, ``datos_legajo``) and renders the template's own ``content``
    block with its partials. Until O01-O04 deliver their React sections, the
    whole legajo is a server-rendered native fragment that React mounts inside
    the shared frame; its documentation script is listed in ``scripts``.
    """

    authentication_classes = [SessionAuthentication]
    permission_classes = [WebGatePermission, OrganizacionListAccess]
    renderer_classes = [JSONRenderer]
    http_method_names = ["get", "head"]

    def get(self, request, pk):
        django_request = request._request  # pylint: disable=protected-access
        vista = OrganizacionDetailView()
        vista.setup(django_request, pk=pk)
        vista.object = vista.get_object()
        context = vista.get_context_data()
        plantilla = get_template(LEGAJO_TEMPLATE)
        contexto = RequestContext(django_request, context)
        with contexto.bind_template(plantilla.template):
            titulo = _bloque(plantilla, "title").nodelist.render(contexto)
            html = _bloque(plantilla, "content").nodelist.render(contexto)
        return Response(
            {
                "title": titulo,
                "html": html,
                "scripts": [static(ruta) for ruta in LEGAJO_SCRIPTS],
                "messages": _pending_messages(django_request),
            }
        )
