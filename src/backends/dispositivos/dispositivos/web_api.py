"""Web API (G1 v1) of the Dispositivos list, detail, map and location for React.

``/api/web/dispositivos/`` is published by the dispositivos backend
(``url_prefixes`` in ``src/backends/config/backends.json``). In a split deploy
the core checks the session and the web prerequisites and signs each request;
the runtime only serves requests its ``WebGateMiddleware`` verified. In the
monolith ``WebGatePermission`` evaluates the same policy locally. After that
the native URL guard applies unchanged (``dispositivos/urls.py``): ANY
``view_dispositivo`` for the list and detail, ALL ``view_dispositivo`` +
``ver_mapa_dispositivo`` for the map and the location lookup.

Each endpoint runs the native view itself (``DispositivoListView``,
``DispositivoDetailView``, ``DispositivoMapView``: scope, search, advanced
filters, pagination, object rule), so it cannot drift from the HTML page; this
module only projects that context to JSON (contract DS01-DS02, #2785).
Read-only: GET/HEAD only. The location lookup keeps its existing effect (it may
persist a definitive Georef result and caches it), exactly as the native GET.
"""

from urllib.parse import quote

from django.contrib import messages
from django.http import Http404
from django.template.defaultfilters import date as date_filter
from django.urls import reverse
from django.utils import formats, timezone
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import NotFound
from rest_framework.permissions import BasePermission
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.views import APIView

from core.decorators import _has_all_permissions, _has_any_permissions
from core.pagination import build_compact_page_range
from core.web_gate import WebGatePermission

from .services import apply_dispositivos_scope, get_dispositivos_queryset
from .services import geolocate_dispositivo
from .views import DispositivoDetailView, DispositivoListView, DispositivoMapView

VIEW = ["dispositivos.view_dispositivo"]
MAPA = ["dispositivos.view_dispositivo", "dispositivos.ver_mapa_dispositivo"]
PAGE_SIZE = 15
INVALID_PAGE = "Página no válida."
MESSAGE_LEVELS = {
    messages.DEBUG: "info",
    messages.INFO: "info",
    messages.SUCCESS: "success",
    messages.WARNING: "warning",
    messages.ERROR: "error",
}


class ViewDispositivo(BasePermission):
    """Same rule as ``permissions_any_required(["...view_dispositivo"])``."""

    def has_permission(self, request, view):
        return _has_any_permissions(request.user, VIEW)


class VerMapaDispositivo(BasePermission):
    """Same rule as ``permissions_all_required(MAPA_PERMISSIONS)``."""

    def has_permission(self, request, view):
        return _has_all_permissions(request.user, MAPA)


class DispositivosWebView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [WebGatePermission, ViewDispositivo]
    renderer_classes = [JSONRenderer]
    http_method_names = ["get", "head"]


def pending_messages(request):
    """Consume queued Django messages exactly as the native page would."""
    django_request = request._request  # pylint: disable=protected-access
    return [
        {"message": str(item), "level": MESSAGE_LEVELS.get(item.level, "info")}
        for item in messages.get_messages(django_request)
    ]


def native_view(view_class, request, **kwargs):
    view = view_class()
    view.setup(request._request, **kwargs)  # pylint: disable=protected-access
    return view


def rendered(value):
    """``{{ value }}`` of a template: local time, localized, then text."""
    return str(formats.localize(timezone.template_localtime(value)))


def _query_prefix(request):
    """Prefix of every ``components/pagination.html`` link (``page`` appended).

    The list does not pass ``query`` to the component, so ``busqueda`` is not
    carried by the page links (native quirk, kept).
    """
    return "".join(
        f"{clave}={quote(valor, safe='/')}&"
        for clave, valor in request.GET.items()
        if clave not in ("page", "busqueda")
    )


def _options(context, user):
    return {
        "titulo": context["titulo"],
        "filters_config": context["filters_config"],
        "favorites": {
            "section": context["seccion_filtros_favoritos"],
            "url": reverse("filtros_favoritos"),
            "detail_url_template": reverse("detalle_filtro_favorito", kwargs={"pk": 0}),
        },
        "add_url": context["add_url"],
        "map_url": context["map_url"],
        "urls": {"list": context["filters_action"], "reset": context["reset_url"]},
        "can_change": user.has_perm("dispositivos.change_dispositivo"),
        "can_delete": user.has_perm("dispositivos.delete_dispositivo"),
    }


def _list_context(request, view_class):
    vista = native_view(view_class, request)
    vista.object_list = vista.get_queryset()
    try:
        return vista.get_context_data()
    except Http404 as exc:
        raise NotFound(INVALID_PAGE) from exc


def _fila(dispositivo):
    return {
        "id": dispositivo.pk,
        "nombre_institucion": dispositivo.nombre_institucion,
        "tipo_dispositivo_display": str(dispositivo.get_tipo_dispositivo_display()),
        "provincia": rendered(dispositivo.provincia),
        "municipio": rendered(dispositivo.municipio),
        "urls": {
            "detail": reverse("dispositivos_detalle", args=[dispositivo.pk]),
            "edit": reverse("dispositivos_editar", args=[dispositivo.pk]),
            "delete": reverse("dispositivos_eliminar", args=[dispositivo.pk]),
        },
    }


class DispositivoListWebView(DispositivosWebView):
    """``GET /api/web/dispositivos/listado/``: the native page of 15 (envelope as Insumos)."""

    def get(self, request):
        context = _list_context(request, DispositivoListView)
        page = context["page_obj"]
        user = request.user
        return Response(
            {
                "count": page.paginator.count,
                "page": page.number,
                "page_size": PAGE_SIZE,
                "pages": page.paginator.num_pages,
                "filters": {
                    "busqueda": request.GET.get("busqueda", ""),
                    "filters": request.GET.get("filters", ""),
                },
                "results": [_fila(item) for item in context["dispositivos"]],
                "is_paginated": bool(context["is_paginated"]),
                "has_next": page.has_next(),
                "has_previous": page.has_previous(),
                "page_range": list(build_compact_page_range(page)),
                "query_prefix": _query_prefix(request),
                **_options(context, user),
                "messages": pending_messages(request),
            }
        )


class DispositivoOptionsWebView(DispositivosWebView):
    """``GET /api/web/dispositivos/options/``: filters config and action flags."""

    def get(self, request):
        context = _list_context(request, DispositivoListView)
        return Response(_options(context, request.user))


# --- Detail (``dispositivos_detail.html``) ------------------------------------


def _item_value(item):
    value = item["value"]
    kind = item.get("kind")
    if kind == "list":
        return [str(chip) for chip in value]
    if kind == "file":
        return value
    return "-" if value == "-" else rendered(value)


def _secciones(secciones):
    return [
        {
            "titulo": seccion["titulo"],
            "icono": seccion["icono"],
            "items": [
                {
                    "label": item["label"],
                    "value": _item_value(item),
                    "kind": item.get("kind", "text"),
                    "wide": bool(item.get("wide")),
                }
                for item in seccion["items"]
            ],
        }
        for seccion in secciones
    ]


class DispositivoDetailWebView(DispositivosWebView):
    """``GET /api/web/dispositivos/<pk>/``: the native legajo (scope 404)."""

    def get(self, request, pk):
        vista = native_view(DispositivoDetailView, request, pk=pk)
        try:
            vista.object = vista.get_object()
        except Http404 as exc:
            raise NotFound() from exc
        dispositivo = vista.object
        context = vista.get_context_data()
        user = request.user
        return Response(
            {
                "id": dispositivo.pk,
                "nombre_institucion": dispositivo.nombre_institucion,
                "meta": {
                    "tipo": (
                        str(dispositivo.get_tipo_dispositivo_display())
                        if dispositivo.tipo_dispositivo
                        else None
                    ),
                    "provincia": (
                        str(dispositivo.provincia) if dispositivo.provincia else None
                    ),
                    "municipio": (
                        str(dispositivo.municipio) if dispositivo.municipio else None
                    ),
                    "actualizado": (
                        date_filter(timezone.localtime(dispositivo.updated_at), "d/m/Y")
                        if dispositivo.updated_at
                        else None
                    ),
                },
                "can_change": user.has_perm("dispositivos.change_dispositivo"),
                "edit_url": reverse("dispositivos_editar", args=[dispositivo.pk]),
                "breadcrumb": [
                    {"text": item["text"], "url": item.get("url")}
                    for item in context["breadcrumb_items"]
                ],
                # Only with ``ver_mapa_dispositivo``, as ``views.py`` builds it.
                "show_map": user.has_perm("dispositivos.ver_mapa_dispositivo"),
                "mapa_query": context.get("mapa_query"),
                "detalle_secciones": _secciones(context["detalle_secciones"]),
                "messages": pending_messages(request),
            }
        )


# --- Map (``dispositivos_map.html``) -------------------------------------------


class DispositivoMapWebView(DispositivosWebView):
    """``GET /api/web/dispositivos/mapa/``: every device of the filtered scope."""

    permission_classes = [WebGatePermission, VerMapaDispositivo]

    def get(self, request):
        context = _list_context(request, DispositivoMapView)
        devices = []
        for device, item in zip(context["dispositivos"], context["map_devices"]):
            devices.append(
                {
                    **item,
                    "municipio": rendered(device.municipio),
                    "street": f"{rendered(device.calle)} {rendered(device.altura)}",
                    "location_url": reverse(
                        "web_dispositivos_ubicacion", args=[device.pk]
                    ),
                }
            )
        return Response(
            {
                "titulo": context["titulo"],
                "devices": devices,
                "provinces": [
                    {"id": pk, "nombre": nombre}
                    for pk, nombre in context["map_provinces"]
                ],
                "filters_config": context["filters_config"],
                "favorites": {
                    "section": context["seccion_filtros_favoritos"],
                    "url": reverse("filtros_favoritos"),
                    "detail_url_template": reverse(
                        "detalle_filtro_favorito", kwargs={"pk": 0}
                    ),
                },
                "location_filters": context["map_location_filters"],
                "initial_device": context["map_initial_device"],
                "urls": {
                    "list": context["filters_action"],
                    "reset": context["reset_url"],
                },
                "messages": pending_messages(request),
            }
        )


class DispositivoLocationWebView(DispositivosWebView):
    """``GET /api/web/dispositivos/<pk>/ubicacion/``: the native lookup body."""

    permission_classes = [WebGatePermission, VerMapaDispositivo]

    def get(self, request, pk):
        queryset = apply_dispositivos_scope(get_dispositivos_queryset(), request.user)
        device = queryset.filter(pk=pk).first()
        if device is None:
            raise NotFound()
        result = geolocate_dispositivo(device)
        return Response(
            result, status=503 if result["status"] == "unavailable" else 200
        )
