"""Web API (G1 v1) of the CDI centres list (CDI09.01) for the React page.

``/api/web/cdi/`` is published by this backend. In a split deploy the core
checks the session and the web prerequisites and signs each request; the
runtime only serves what its ``WebGateMiddleware`` verified. In the monolith
``WebGatePermission`` evaluates the same policy locally. After that the native
URL guard applies unchanged: ``centrodeinfancia.view_centrodeinfancia`` through
the same predicate as ``permissions_any_required`` (superuser bypass included).

The endpoint runs ``CentroDeInfanciaListView`` itself (scope, search, advanced
filters, ordering, exact pages of 10 and column preferences), so it cannot
drift from the HTML page; this module only projects its context to JSON. Cell
texts follow ``partials/rows.html``. Read-only: GET and HEAD only. The CSV
export and the children PDF stay native downloads.
"""

from urllib.parse import quote

from django.http import Http404
from django.urls import reverse
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import NotFound
from rest_framework.permissions import BasePermission
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.views import APIView

from centrodeinfancia.views import CentroDeInfanciaListView
from centrodeinfancia.web_api import breadcrumb, pending_messages
from core.decorators import _has_any_permissions
from core.pagination import build_compact_page_range
from core.templatetags.custom_filters import has_any_perm
from core.web_gate import WebGatePermission

VER_CENTRO = ["centrodeinfancia.view_centrodeinfancia"]
PERMISO_EXPORTAR = "auth.role_exportar_a_csv"
NBSP = " "


class PuedeVerCentros(BasePermission):
    """Same rule as the native ``permissions_any_required`` on the list URL."""

    def has_permission(self, request, view):
        return _has_any_permissions(request.user, VER_CENTRO)


def _query_prefix(request):
    """Prefix of every ``components/pagination.html`` link (``page`` appended)."""
    busqueda = request.GET.get("busqueda", "")
    prefix = f"busqueda={quote(busqueda, safe='/')}&" if busqueda else ""
    return prefix + "".join(
        f"{clave}={quote(valor, safe='/')}&"
        for clave, valor in request.GET.items()
        if clave not in ("page", "busqueda")
    )


def _celda(centro, clave):
    """One cell of ``partials/rows.html``: visible text, ``data-*`` sort value, link."""
    if clave == "nombre":
        return {
            "text": centro.nombre,
            "sort": centro.nombre,
            "url": reverse("centrodeinfancia_detalle", args=[centro.pk]),
        }
    if clave == "tiene_nomina":
        valor = "Si" if centro.tiene_nomina else "No"
        return {"text": valor, "sort": valor, "url": None}
    if clave == "referente":
        nombre = centro.nombre_referente or ""
        apellido = centro.apellido_referente or ""
        separador = NBSP if nombre and apellido else ""
        return {
            "text": f"{nombre}{separador}{apellido}" if nombre or apellido else "-",
            "sort": f"{nombre} {apellido}",
            "url": None,
        }
    valor = getattr(centro, clave)
    texto = str(valor) if valor else ""
    return {"text": texto or "-", "sort": texto, "url": None}


def _fila(centro, claves):
    return {
        "id": centro.pk,
        "cells": [_celda(centro, clave) for clave in claves],
        "urls": {
            "detail": reverse("centrodeinfancia_detalle", args=[centro.pk]),
            "edit": reverse("centrodeinfancia_editar", args=[centro.pk]),
            "delete": reverse("centrodeinfancia_eliminar", args=[centro.pk]),
        },
    }


class CentrosListWebView(APIView):
    """``GET /api/web/cdi/centros/``: the native list as JSON."""

    authentication_classes = [SessionAuthentication]
    permission_classes = [WebGatePermission, PuedeVerCentros]
    renderer_classes = [JSONRenderer]
    http_method_names = ["get", "head"]

    def get(self, request):
        django_request = request._request  # pylint: disable=protected-access
        vista = CentroDeInfanciaListView()
        vista.setup(django_request)
        try:
            vista.object_list = vista.get_queryset()
            context = vista.get_context_data()
        except Http404 as exc:
            raise NotFound() from exc
        page = context["page_obj"]
        claves = list(context["active_columns"])
        titulos = {
            col["key"]: str(col["title"])
            for col in context["column_config"]["available"]
        }
        resultados = [_fila(centro, claves) for centro in context["centros"]]
        modal = None
        if context.get("mostrar_modal_nomina_ninos"):
            modal = {
                "provincias": [
                    {"id": provincia.pk, "nombre": provincia.nombre}
                    for provincia in context["nomina_ninos_provincias"]
                ],
                "url": reverse("centrodeinfancia_nomina_ninos_pdf"),
            }
        return Response(
            {
                "breadcrumb": breadcrumb(context["breadcrumb_items"]),
                "filters_config": context["filters_config"],
                "favorites": {
                    "section": "",
                    "url": reverse("filtros_favoritos"),
                    "detail_url_template": reverse(
                        "detalle_filtro_favorito", kwargs={"pk": 0}
                    ),
                },
                "columns": context["column_config"],
                "headers": [
                    {"key": clave, "title": titulos.get(clave, clave)}
                    for clave in claves
                ],
                "results": resultados,
                "page": {
                    "is_paginated": bool(context["is_paginated"]),
                    "number": page.number,
                    "previous": (
                        page.previous_page_number() if page.has_previous() else None
                    ),
                    "next": page.next_page_number() if page.has_next() else None,
                    "range": list(build_compact_page_range(page)),
                    # An empty page is falsy, so the native component omits the total.
                    "count": page.paginator.count if resultados else None,
                    "query_prefix": _query_prefix(django_request),
                },
                "can_export": bool(
                    request.user.is_superuser
                    or has_any_perm(request.user, PERMISO_EXPORTAR)
                ),
                "nomina_ninos": modal,
                "urls": {
                    "list": context["filters_action"],
                    "add": reverse("centrodeinfancia_crear"),
                    "export": reverse("centrodeinfancia_exportar"),
                },
                "messages": pending_messages(django_request),
            }
        )
