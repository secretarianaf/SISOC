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
stays the native GET ``/equipo-tecnico/exportar/``. List and detail are
read-only (GET); create, edit and soft delete run the native ``post()``.
"""

from django import forms
from django.contrib import messages
from django.http import Http404
from django.template.defaultfilters import date as date_filter
from django.template.defaultfilters import upper, urlencode
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
from duplas.views import (
    DuplaCreateView,
    DuplaDeleteView,
    DuplaDetailView,
    DuplaListView,
    DuplaUpdateView,
)

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


# --- DU01.02: create, edit and soft delete ----------------------------------
# GET returns what the native form or confirmation renders; POST runs the
# native view's own ``post()`` (ModelForm, signals, soft delete and messages).
# A redirect becomes ``{"ok": true, "redirect": ...}``; an invalid form the
# same payload with its errors (400), consuming the messages it rendered.


def _choice_value(value):
    return "" if value is None else str(getattr(value, "value", value))


def _bound(form, name):
    value = form[name].value()
    if isinstance(form.fields[name], forms.ModelMultipleChoiceField):
        return [_choice_value(item) for item in value or []]
    if isinstance(value, (list, tuple)):
        return [_choice_value(item) for item in value]
    return _choice_value(value)


def _field(form, name):
    field = form.fields[name]
    payload = {
        "label": str(form[name].label),
        "required": field.required,
        "help_text": str(field.help_text or ""),
        "value": _bound(form, name),
    }
    if name == "nombre":
        payload["max_length"] = field.max_length
    else:
        payload["choices"] = [
            {"value": _choice_value(value), "label": str(label)}
            for value, label in field.choices
        ]
    return payload


def _form_payload(form, dupla, request):
    return {
        "title": "Editar Equipo técnico",
        "fields": {
            name: _field(form, name)
            for name in ("nombre", "estado", "tecnico", "abogado")
        },
        "errors": {
            name: [
                {"message": str(error["message"]), "code": error["code"] or ""}
                for error in errors
            ]
            for name, errors in form.errors.get_json_data().items()
        },
        "coordinador": (
            _nombre(dupla.coordinador) if dupla and dupla.coordinador else None
        ),
        "urls": {"cancel": reverse("dupla_list")},
        "messages": pending_messages(request),
    }


class _DuplaFormWebView(DuplasWebView):
    http_method_names = ["get", "post"]
    view_class = None

    def _view(self, request, pk=None):
        kwargs = {} if pk is None else {"pk": pk}
        return native_view(self.view_class, request, **kwargs)

    def _object(self, vista):
        # ``CreateView.post`` sets it; the native override does not, so an
        # invalid native create crashes rendering (500). See the change record.
        vista.object = None
        return vista.object

    def get(self, request, pk=None):
        vista = self._view(request, pk)
        dupla = self._object(vista)
        return Response(_form_payload(vista.get_form(), dupla, request))

    def post(self, request, pk=None):
        vista = self._view(request, pk)
        dupla = self._object(vista)
        respuesta = vista.post(request._request)  # pylint: disable=protected-access
        if respuesta.status_code == 302:
            return Response({"ok": True, "redirect": respuesta["Location"]})
        form = respuesta.context_data["form"]
        return Response(_form_payload(form, dupla, request), status=400)


class DuplaCreateWebView(_DuplaFormWebView):
    """``/api/web/comedores/duplas/crear/``: ``DuplaCreateView`` as JSON."""

    view_class = DuplaCreateView


class DuplaUpdateWebView(_DuplaFormWebView):
    """``/api/web/comedores/duplas/<pk>/editar/``: ``DuplaUpdateView`` as JSON."""

    view_class = DuplaUpdateView

    def _object(self, vista):
        try:
            vista.object = vista.get_object()
        except Http404 as exc:
            raise NotFound() from exc
        return vista.object


class DuplaDeleteWebView(DuplasWebView):
    """``/api/web/comedores/duplas/<pk>/eliminar/``: confirmation and soft delete."""

    http_method_names = ["get", "post"]

    def _view(self, request, pk):
        vista = native_view(DuplaDeleteView, request, pk=pk)
        try:
            vista.object = vista.get_object()
        except Http404 as exc:
            raise NotFound() from exc
        return vista

    def get(self, request, pk):
        vista = self._view(request, pk)
        context = vista.get_context_data()
        dupla = context["object"]
        return Response(
            {
                "id": dupla.pk,
                "object_name": upper(dupla.nombre),
                "title": "Dar de baja Equipo técnico",
                "confirm_text": "Dar de baja Equipo técnico",
                "cancel_text": context["cancel_text"],
                "cascade_preview": context.get("cascade_preview"),
                "urls": {"cancel": reverse("dupla_list")},
                "messages": pending_messages(request),
            }
        )

    def post(self, request, pk):
        vista = self._view(request, pk)
        respuesta = vista.post(request._request)  # pylint: disable=protected-access
        return Response({"ok": True, "redirect": respuesta["Location"]})
