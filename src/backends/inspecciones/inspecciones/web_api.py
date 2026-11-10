"""Web API (G1 v1) of the backoffice Actas tab for the React screen.

``/api/web/inspecciones/`` is published by this backend (``url_prefixes`` in
``src/backends/config/backends.json``). In a split deploy the core checks the
session and the web prerequisites and signs each request; the runtime only
serves requests its ``WebGateMiddleware`` verified. In the monolith
``WebGatePermission`` evaluates the same policy locally. After that the
native rule applies unchanged: session plus ``puede_gestionar``.

The list reuses ``views_actas.ActasView`` itself (filters, order, 25 per page,
invalid page 404, breadcrumb and initials), so it cannot drift from the HTML
page; this module only projects that context to JSON. Read-only: GET only.
"""

from django.http import Http404
from django.urls import NoReverseMatch, reverse
from django.utils import timezone
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import NotFound
from rest_framework.permissions import BasePermission
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.views import APIView

from core.pagination import build_compact_page_range
from core.web_gate import WebGatePermission
from inspecciones.access import puede_gestionar
from inspecciones.views_actas import ActasView
from inspecciones.views_ajax import InspectoresAjaxView

FILTROS = ("fecha", "inspector", "provincia", "estado", "numero")
PESTANAS = (
    ("tablero", "Tablero", "inspecciones_tablero"),
    ("escuelas", "Escuelas", "inspecciones_panel"),
    ("asignaciones", "Asignaciones", "inspecciones_asignaciones"),
    ("actas", "Actas", "inspecciones_actas"),
)


class PuedeGestionar(BasePermission):
    """Same rule as ``GestionInspeccionesMixin``: management of the program."""

    def has_permission(self, request, view):
        return puede_gestionar(request.user)


class _WebView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [WebGatePermission, PuedeGestionar]
    renderer_classes = [JSONRenderer]


def _pestanas():
    """Tabs of ``_pestanas.html``: Tablero only if its route exists."""
    pestanas = []
    for clave, etiqueta, nombre in PESTANAS:
        try:
            url = reverse(nombre)
        except NoReverseMatch:
            continue
        pestanas.append({"id": clave, "label": etiqueta, "url": url})
    return pestanas


def _fila(fila):
    acta = fila["acta"]
    cerrada = acta.cerrada_at
    return {
        "numero": acta.numero,
        "url": reverse("inspecciones_acta_detalle", args=[acta.numero]),
        "anulada": acta.estado == acta.Estado.ANULADA,
        "prueba": acta.es_prueba,
        "escuela": {
            "nombre": fila["escuela"]["nombre"] or "",
            "cueanexo": fila["escuela"]["cueanexo"] or "",
            "provincia": fila["escuela"]["provincia"] or "",
            "localidad": str(fila["escuela"]["localidad"] or ""),
        },
        "turno": fila["turno"],
        "inspector": acta.inspector.get_full_name() or acta.inspector.username,
        "fecha": acta.fecha_visita.strftime("%d/%m/%Y") if acta.fecha_visita else "",
        "hora": timezone.localtime(cerrada).strftime("%H:%M") if cerrada else "",
        "firma": acta.firma_tipo if acta.firma_tipo in ("firma", "excepcion") else "",
        "notificacion": (
            "cargada" if acta.notificacion_estado == "cargada" else "pendiente"
        ),
    }


def _pagina(context):
    page = context["page_obj"]
    paginator = page.paginator
    return {
        "number": page.number,
        "count": paginator.count,
        "start_index": page.start_index() if paginator.count else 0,
        "end_index": page.end_index() if paginator.count else 0,
        "has_other_pages": page.has_other_pages(),
        "previous": page.previous_page_number() if page.has_previous() else None,
        "next": page.next_page_number() if page.has_next() else None,
        "range": [
            "…" if numero in ("...", "…") else numero
            for numero in build_compact_page_range(page)
        ],
        "query_without_page": context["parametros_sin_pagina"],
    }


def _layout(context):
    migas = context["breadcrumb_items"]
    return {
        "breadcrumb": [
            {
                "text": item["text"],
                "url": item.get("url") if indice < len(migas) - 1 else None,
            }
            for indice, item in enumerate(migas)
        ],
        "display_name": context["request"].user.get_full_name()
        or context["request"].user.get_username(),
        "role": context["rol_usuario"],
        "initials": context["iniciales_usuario"],
    }


class ActasWebView(_WebView):
    """``GET /api/web/inspecciones/actas/``: the Actas tab with its filters."""

    http_method_names = ["get", "head"]

    def get(self, request):
        vista = ActasView()
        vista.setup(request._request)  # pylint: disable=protected-access
        try:
            vista.object_list = vista.get_queryset()
            context = vista.get_context_data()
        except Http404 as exc:
            raise NotFound() from exc
        context["request"] = request
        filtro = context["filtro"]
        parametros = request.query_params
        return Response(
            {
                "layout": _layout(context),
                "tabs": _pestanas(),
                "filters": {
                    **{clave: parametros.get(clave, "") for clave in FILTROS},
                    "inspector": context["inspector_filtro"],
                },
                "options": {
                    "provincias": [
                        {"id": provincia.pk, "nombre": provincia.nombre}
                        for provincia in filtro.fields["provincia"].queryset
                    ],
                    "estados": [
                        {"value": valor, "label": str(etiqueta)}
                        for valor, etiqueta in filtro.fields["estado"].choices
                    ],
                    "inspectores_url": reverse("inspecciones_web_inspectores")
                    + "?alcance=programa",
                },
                "has_query": bool(parametros),
                "results": [_fila(fila) for fila in context["filas"]],
                "page": _pagina(context),
            }
        )


class InspectoresWebView(_WebView):
    """``GET /api/web/inspecciones/inspectores/``: the J2 inspector search.

    Same service, threshold (3), limit (20) and ``alcance=programa`` scope as
    ``views_ajax.InspectoresAjaxView``; the response is ``{"results": [...]}``.
    Like that view it only answers GET.
    """

    http_method_names = ["get"]

    def get(self, request):
        django_request = request._request  # pylint: disable=protected-access
        return Response({"results": InspectoresAjaxView().resultados(django_request)})
