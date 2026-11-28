"""Web API (G1 v1) of the comedor legajo (CO07): ``/api/web/comedores/comedores/``.

``/api/web/comedores/`` is published by the comedores backend. In a split
deploy the core checks the session and the web prerequisites and signs each
request; the runtime only serves requests its ``WebGateMiddleware`` verified.
In the monolith ``WebGatePermission`` evaluates the same policy locally. After
that the native route guard applies unchanged (superuser bypass included):

- list: ``permissions_any_required(["comedores.view_comedor",
  "admisiones.view_admision", "acompanamientos.view_informacionrelevante"])``;
- baja: ``permissions_any_required(["comedores.delete_comedor"])``, plus the
  object scope of the native ``ComedorDeleteView`` (a comedor outside the user's
  scope is a 404).

The list runs the native ``ComedorListView`` itself (``setup()``, queryset with
the user scope and the advanced filters, ``NoCountPaginator``, column
preferences and context), so it cannot drift from ``comedor_list.html``; this
module only projects that context to JSON. The CSV export stays the native GET.

The baja runs the native ``ComedorDeleteView`` itself (cascade preview, logical
delete with the actor, native success message); the message stays queued for the
list the redirect lands on.
"""

from django.contrib import messages
from django.http import HttpResponseRedirect
from django.template import Context, Template
from django.urls import reverse
from rest_framework.authentication import SessionAuthentication
from rest_framework import status
from rest_framework.permissions import BasePermission
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.views import APIView

# The exact predicates of the native URL decorators.
from core.decorators import _has_any_permissions
from core.pagination import build_compact_page_range
from core.soft_delete.view_helpers import build_delete_preview
from core.templatetags.custom_filters import has_any_perm, has_perm_code
from core.web_gate import WebGatePermission
from comedores.views.comedor import ComedorDeleteView, ComedorListView

LIST_PERMISSIONS = [
    "comedores.view_comedor",
    "admisiones.view_admision",
    "acompanamientos.view_informacionrelevante",
]
# ``comedor_list.html`` arguments of ``components/search_bar.html``.
EXPORT_PERMISSIONS = LIST_PERMISSIONS
EXPORT_REQUIRED_PERMISSION = "auth.role_exportar_a_csv"
EXPORT_ADMIN_PERMISSIONS = (
    "auth.role_admin,auth.role_administrador,auth.role_superadmin"
)
DELETE_PERMISSIONS = ["comedores.delete_comedor"]
MESSAGE_LEVELS = {
    messages.DEBUG: "info",
    messages.INFO: "info",
    messages.SUCCESS: "success",
    messages.WARNING: "warning",
    messages.ERROR: "error",
}
# Columns whose ``<th>`` is ``sortable`` (client-side, ``listSort.js``).
SORTABLE = ("nombre", "validacion")

# One ``<td>`` per column of ``components/comedor_table.html``, rendered with the
# same filters so defaults and localization cannot drift.
_SOURCES = {
    "id": "{{ c.id }}",
    "tipo": '{{ c.tipocomedor__nombre|default_if_none:"Sin información" }}',
    "organizacion": '{{ c.organizacion__nombre|default_if_none:"Sin organización" }}',
    "programa": '{{ c.programa__nombre|default_if_none:"Sin programa" }}',
    "mes_ejecucion": (
        "{% if c.mes_ejecucion is None %}-{% elif c.mes_ejecucion > 0 %}"
        "{{ c.mes_ejecucion }}/{{ c.duracion_convenio }}"
        "{% else %}{{ c.mes_ejecucion }}{% endif %}"
    ),
    "dupla": '{{ c.dupla__nombre|default_if_none:"Sin dupla" }}',
    "estado_general": '{{ c.estado_general|default_if_none:"Sin estado" }}',
    "estado_actividad": (
        "{{ c.ultimo_estado__estado_general__estado_actividad__estado"
        '|default_if_none:"Sin estado" }}'
    ),
    "estado_proceso": (
        "{{ c.ultimo_estado__estado_general__estado_proceso__estado"
        '|default_if_none:"Sin estado" }}'
    ),
    "estado_detalle": (
        "{{ c.ultimo_estado__estado_general__estado_detalle__estado"
        '|default_if_none:"Sin estado" }}'
    ),
    "provincia": '{{ c.provincia__nombre|default_if_none:"Sin provincia" }}',
    "municipio": '{{ c.municipio__nombre|default_if_none:"Sin municipio" }}',
    "localidad": '{{ c.localidad__nombre|default_if_none:"Sin localidad" }}',
    "barrio": '{{ c.barrio|default_if_none:"Sin barrio" }}',
    "partido": '{{ c.partido|default_if_none:"Sin partido" }}',
    "calle": '{{ c.calle|default_if_none:"Sin calle" }}',
    "numero": '{{ c.numero|default_if_none:"S/N" }}',
    "direccion": (
        '{{ c.calle|default_if_none:"Sin calle" }} '
        '{{ c.numero|default_if_none:"S/N" }}'
    ),
    "referente": (
        '{{ c.referente__nombre|default_if_none:"Sin" }} '
        '{{ c.referente__apellido|default_if_none:"información" }}'
    ),
    "referente_celular": '{{ c.referente__celular|default_if_none:"Sin celular" }}',
    "fecha_validado": '{{ c.fecha_validado|date:"d/m/Y"|default_if_none:"Sin fecha" }}',
    "nombre": "{{ c.nombre }}",
    "validacion": "{{ c.estado_validacion }}",
    "fecha": '{{ c.fecha_validado|date:"d/m/Y" }}',
}
_TEMPLATES = {key: Template(source) for key, source in _SOURCES.items()}


class VerComedores(BasePermission):
    def has_permission(self, request, view):
        return _has_any_permissions(request.user, LIST_PERMISSIONS)


class BajaComedor(BasePermission):
    def has_permission(self, request, view):
        return _has_any_permissions(request.user, DELETE_PERMISSIONS)


class _WebView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [WebGatePermission, VerComedores]
    renderer_classes = [JSONRenderer]
    http_method_names = ["get", "head"]


def pending_messages(request):
    """Consume queued Django messages exactly as the native page would."""
    return [
        {"message": str(m), "level": MESSAGE_LEVELS.get(m.level, "info")}
        for m in messages.get_messages(request)
    ]


def _native(view_class, request, **kwargs):
    view = view_class()
    view.setup(request._request, **kwargs)  # pylint: disable=protected-access
    return view


def _render(key, comedor):
    return _TEMPLATES[key].render(Context({"c": comedor})).strip()


def _cell(key, comedor):
    """Projection of one ``<td>`` of ``comedor_table.html``."""
    if key == "ubicacion":
        lineas = [
            _render("provincia", comedor),
            f"{_render('municipio', comedor)} / {_render('localidad', comedor)}",
        ]
        if comedor.get("barrio"):
            lineas.append(str(comedor["barrio"]))
        return {"key": key, "lines": lineas}
    if key == "validacion":
        return {
            "key": key,
            "value": _render("validacion", comedor),
            "date": (
                _render("fecha", comedor) if comedor.get("fecha_validado") else None
            ),
        }
    if key == "judicializado":
        valor = comedor.get("es_judicializado")
        return {"key": key, "text": "-" if valor is None else "Sí" if valor else "No"}
    return {"key": key, "text": _render(key, comedor)}


def _row(comedor, active):
    return {
        "id": comedor["id"],
        "nombre": str(comedor["nombre"]),
        "cells": [_cell(key, comedor) for key in active],
        "urls": {
            "detalle": reverse("comedor_detalle", args=[comedor["id"]]),
            "editar": reverse("comedor_editar", args=[comedor["id"]]),
            "eliminar": reverse("comedor_eliminar", args=[comedor["id"]]),
        },
    }


def _query_prefix(request):
    """Link prefix of ``components/pagination.html`` (no ``busqueda`` here)."""
    plantilla = Template("{{ v|urlencode }}")
    return "".join(
        f"{clave}={plantilla.render(Context({'v': valor})).strip()}&"
        for clave, valor in request.GET.items()
        if clave not in ("page", "busqueda")
    )


def _can_export(user):
    if user.is_superuser or has_any_perm(user, EXPORT_ADMIN_PERMISSIONS):
        return True
    return bool(
        has_any_perm(user, EXPORT_PERMISSIONS)
        and has_perm_code(user, EXPORT_REQUIRED_PERMISSION)
    )


class ComedoresListWebView(_WebView):
    """``GET /api/web/comedores/comedores/``: ``comedor_list.html``."""

    def get(self, request):
        vista = _native(ComedorListView, request)
        vista.object_list = vista.get_queryset()
        context = vista.get_context_data()
        page = context["page_obj"]
        active = list(context["active_columns"])
        titles = {c["key"]: c["title"] for c in context["column_config"]["available"]}
        return Response(
            {
                "breadcrumb": [
                    {"text": item["text"], "url": item.get("url")}
                    for item in context["breadcrumb_items"]
                ],
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
                    "export": reverse("comedor_export"),
                },
                "can_export": _can_export(request.user),
                "columns": context["column_config"],
                "headers": [
                    {
                        "key": key,
                        "title": titles.get(key, key),
                        "sortable": key in SORTABLE,
                    }
                    for key in active
                ],
                "results": [_row(c, active) for c in context["comedores"]],
                "page": {
                    "is_paginated": context["is_paginated"],
                    "number": page.number,
                    "previous": (
                        page.previous_page_number() if page.has_previous() else None
                    ),
                    "next": page.next_page_number() if page.has_next() else None,
                    "range": [
                        "…" if numero in ("...", "…") else numero
                        # An empty page has no ``page_range``: the template's
                        # ``compact_page_range`` fallback, which is not shown.
                        for numero in context.get("page_range")
                        or build_compact_page_range(page)
                    ],
                    "query_without_page": _query_prefix(request),
                },
                "messages": pending_messages(request),
            }
        )


class ComedorBajaWebView(APIView):
    """``GET/POST /api/web/comedores/comedores/<pk>/baja/``: ``comedor_confirm_delete.html``."""

    authentication_classes = [SessionAuthentication]
    permission_classes = [WebGatePermission, BajaComedor]
    renderer_classes = [JSONRenderer]
    http_method_names = ["get", "head", "post"]

    @staticmethod
    def _vista(request, pk):
        vista = _native(ComedorDeleteView, request, pk=pk)
        # The scoped queryset: outside the user's scope is the native 404.
        vista.object = vista.get_object()
        return vista

    def get(self, request, pk):
        comedor = self._vista(request, pk).object
        return Response(
            {
                "id": comedor.pk,
                "nombre": comedor.nombre,
                "cascade_preview": build_delete_preview(comedor),
                "urls": {
                    "cancel": reverse("comedor_detalle", args=[comedor.pk]),
                    "list": reverse("comedores"),
                },
                "messages": pending_messages(request),
            }
        )

    def post(self, request, pk):
        django_request = request._request  # pylint: disable=protected-access
        respuesta = self._vista(request, pk).post(django_request)
        if isinstance(respuesta, HttpResponseRedirect):
            # The native success message stays queued for the list it lands on.
            return Response({"redirect": respuesta.url})
        return Response(
            {"error": "No se pudo dar de baja."}, status=status.HTTP_409_CONFLICT
        )
