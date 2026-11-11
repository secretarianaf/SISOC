"""Web API (G1 v1) of the DataCalle back office operativos for React (DC01.01-DC01.03).

``/api/web/dispositivos/datacalle/`` belongs to the dispositivos backend (one
``api/web/<vertical>/`` prefix per runtime, ``src/backends/config/backends.json``).
In a split deploy the core checks the session and the web prerequisites and
signs each request; the runtime only serves what its ``WebGateMiddleware``
verified. In the monolith ``WebGatePermission`` evaluates the same policy.
After that the native URL guard applies unchanged (``datacalle/urls.py``):
ANY ``view_relevamiento`` / ``add_relevamiento`` / ``change_relevamiento`` /
``delete_relevamiento``, raised as 403 before the object is looked up.

Each endpoint runs the native view (``RelevamientoListView``,
``RelevamientoDetailView``, the create/update form views,
``RelevamientoDeleteView`` and ``RelevamientoCerrarView``: provincial scope,
filters, pagination, ``RelevamientoForm`` with ``actor``, the services that
save, close and soft-delete) and only projects it to JSON (contract DC01-DC02,
#2785). Like the native views: no success message on create, edit or delete;
the close queues the same ``success``/``info`` message and is idempotent.
"""

from django.contrib import messages
from django.forms import CheckboxInput, DateInput, Select, SelectMultiple, Textarea
from django.http import Http404
from django.template.defaultfilters import date as date_filter
from django.urls import reverse
from django.utils import timezone
from rest_framework.exceptions import NotFound
from rest_framework.permissions import BasePermission
from rest_framework.response import Response

from core.decorators import _has_any_permissions
from core.web_gate import WebGatePermission
from datacalle.models import Relevamiento
from datacalle.services import cerrar_relevamiento
from datacalle.views import (
    RelevamientoCerrarView,
    RelevamientoCreateView,
    RelevamientoDeleteView,
    RelevamientoDetailView,
    RelevamientoListView,
    RelevamientoUpdateView,
    cargar_dispositivos,
    cargar_relevadores,
)
from dispositivos.web_api import (
    DispositivosWebView,
    _list_context,
    _query_prefix,
    native_view,
    pending_messages,
    rendered,
)

PAGE_SIZE = 15
CERRADO = "El relevamiento quedó cerrado."
YA_CERRADO = "El relevamiento ya estaba cerrado."


def _native_permission(codename):
    """Same rule as ``permissions_any_required(["datacalle.<codename>"])``."""

    class NativePermission(BasePermission):
        def has_permission(self, request, view):
            return _has_any_permissions(request.user, [f"datacalle.{codename}"])

    NativePermission.__name__ = f"Datacalle_{codename}"
    return NativePermission


VIEW = _native_permission("view_relevamiento")
ADD = _native_permission("add_relevamiento")
CHANGE = _native_permission("change_relevamiento")
DELETE = _native_permission("delete_relevamiento")


class DataCalleWebView(DispositivosWebView):
    """Session + G1 gate, then the native permission of each route."""

    permission_classes = [WebGatePermission, VIEW]


def _django(request):
    return request._request  # pylint: disable=protected-access


def _native_object(view_class, request, pk):
    vista = native_view(view_class, request, pk=pk)
    try:
        vista.object = vista.get_object()
    except Http404 as exc:
        raise NotFound() from exc
    return vista


def _name(user):
    """``user.get_full_name|default:user.username`` of the templates."""
    return user.get_full_name() or user.username


def _datetime(value, fmt):
    return date_filter(timezone.template_localtime(value), fmt) if value else ""


def _choices(choices):
    return [{"value": str(value), "label": str(label)} for value, label in choices]


def _detail_url(pk):
    return reverse("datacalle_relevamientos_detalle", args=[pk])


# --- DC01.01 list (``relevamiento_list.html``) -------------------------------


def _fila(relevamiento):
    return {
        "id": str(relevamiento.pk),
        "denominacion": relevamiento.denominacion,
        "fase_display": str(relevamiento.get_fase_display()),
        "lugar": relevamiento.lugar,
        "modalidad_papel": relevamiento.modalidad_papel,
        "provincia": rendered(relevamiento.provincia),
        "zonas": relevamiento.zonas,
        "fecha_inicio": date_filter(relevamiento.fecha_inicio, "d/m/y"),
        "fecha_fin": date_filter(relevamiento.fecha_fin, "d/m/y"),
        "dias": relevamiento.dias,
        "equipo": relevamiento.equipo.count(),
        "estado": relevamiento.estado,
        "estado_display": str(relevamiento.get_estado_display()),
        "urls": {
            "detail": _detail_url(relevamiento.pk),
            "edit": reverse("datacalle_relevamientos_editar", args=[relevamiento.pk]),
        },
    }


class RelevamientoListWebView(DataCalleWebView):
    """``GET relevamientos/``: the native page of 15, filters and summary."""

    def get(self, request):
        context = _list_context(request, RelevamientoListView)
        page = context["page_obj"]
        return Response(
            {
                "count": page.paginator.count,
                "page": page.number,
                "page_size": PAGE_SIZE,
                "pages": page.paginator.num_pages,
                "filters": {
                    "busqueda": context["busqueda_actual"],
                    "estado": context["estado_actual"],
                    "fase": context["fase_actual"],
                },
                "results": [_fila(item) for item in context["relevamientos"]],
                "is_paginated": bool(context["is_paginated"]),
                "has_next": page.has_next(),
                "has_previous": page.has_previous(),
                "page_range": list(_page_range(page)),
                "query_prefix": _query_prefix(request),
                # Whole scope, never the filtered page (native quirk, kept).
                "resumen": context["resumen"],
                "estados": _choices(context["estados"]),
                "fases": _choices(context["fases"]),
                "add_url": context["add_url"],
                "can_change": request.user.has_perm("datacalle.change_relevamiento"),
                "messages": pending_messages(request),
            }
        )


def _page_range(page):
    # pylint: disable-next=import-outside-toplevel
    from core.pagination import build_compact_page_range

    return build_compact_page_range(page)


# --- DC01.01 detail (``relevamiento_detail.html``) ---------------------------


def _integrante(user):
    inicial = (user.first_name[:1] or user.username[:1]).upper()
    return {
        "iniciales": inicial + user.last_name[:1].upper(),
        "nombre": _name(user),
        "dni": getattr(getattr(user, "profile", None), "dni", "") or "",
    }


def _cierre(relevamiento, observacion):
    if not relevamiento.fecha_cierre:
        return None
    return {
        "fecha": _datetime(relevamiento.fecha_cierre, "d/m/Y H:i"),
        "por": _name(relevamiento.cerrado_por) if relevamiento.cerrado_por else None,
        # ``{% if relevamiento.lat %}``: a latitude of 0 shows as «—» (kept).
        "gps": (
            f"{rendered(relevamiento.lat)}, {rendered(relevamiento.lon)}"
            if relevamiento.lat
            else None
        ),
        "observacion_asentamiento": [str(item) for item in observacion],
        "otra_observacion": relevamiento.otra_observacion,
    }


def _caso(caso):
    return {
        "id": str(caso.pk),
        "codigo": caso.codigo_entrevistado,
        "persona": caso.persona_entrevistada_etiqueta,
        "lugar": caso.lugar_hallazgo,
        "sin_entrevista_por_franja": caso.sin_entrevista_por_franja,
        "estado": caso.estado,
        "estado_display": str(caso.get_estado_display()),
        "es_formulario_menores": caso.es_formulario_menores,
        "cargado": _datetime(caso.fecha_inicio, "d/m/y H:i"),
        # The native link is shown without checking ``view_encuesta`` (kept).
        "url": reverse("datacalle_casos_detalle", args=[caso.pk]),
    }


class RelevamientoDetailWebView(DataCalleWebView):
    """``GET relevamientos/<uuid>/``: the native ficha (scope 404, 50 cases max)."""

    def get(self, request, pk):
        vista = _native_object(RelevamientoDetailView, request, pk)
        context = vista.get_context_data()
        relevamiento, user = vista.object, request.user
        can_change = user.has_perm("datacalle.change_relevamiento")
        return Response(
            {
                "id": str(relevamiento.pk),
                "denominacion": relevamiento.denominacion,
                "estado": relevamiento.estado,
                "estado_display": str(relevamiento.get_estado_display()),
                "provincia": rendered(relevamiento.provincia),
                "municipio": (
                    rendered(relevamiento.municipio) if relevamiento.municipio else None
                ),
                "zonas": relevamiento.zonas,
                "dias": relevamiento.dias,
                "fase": relevamiento.fase,
                "fase_display": str(relevamiento.get_fase_display()),
                "lugar": relevamiento.lugar,
                "localidades": [loc.nombre for loc in relevamiento.localidades.all()],
                "fecha_inicio": date_filter(relevamiento.fecha_inicio, "d/m/Y"),
                "fecha_fin": date_filter(relevamiento.fecha_fin, "d/m/Y"),
                "modalidad_papel": relevamiento.modalidad_papel,
                "creado_por": (
                    _name(relevamiento.creado_por) if relevamiento.creado_por else None
                ),
                "resumen_casos": context["resumen_casos"],
                "equipo": [_integrante(u) for u in relevamiento.equipo.all()],
                "observaciones": relevamiento.observaciones,
                "cierre": _cierre(relevamiento, context["observacion_asentamiento"]),
                "casos": [_caso(caso) for caso in context["encuestas"]],
                "breadcrumb": [
                    {"text": item["text"], "url": item.get("url")}
                    for item in context["breadcrumb_items"]
                ],
                "can_change": can_change,
                "can_close": can_change
                and relevamiento.estado != Relevamiento.Estado.FINALIZADO,
                "can_delete": user.has_perm("datacalle.delete_relevamiento"),
                "urls": {
                    "list": reverse("datacalle_relevamientos_listar"),
                    "edit": reverse(
                        "datacalle_relevamientos_editar", args=[relevamiento.pk]
                    ),
                    "close": reverse("web_datacalle_cerrar", args=[relevamiento.pk]),
                    "delete": reverse(
                        "datacalle_relevamientos_eliminar", args=[relevamiento.pk]
                    ),
                },
                "messages": pending_messages(request),
            }
        )


# --- DC01.02 form (``relevamiento_form.html``) -------------------------------


def _widget(widget):
    for kind, cls in (
        ("checkbox", CheckboxInput),
        ("textarea", Textarea),
        ("date", DateInput),
        ("selectmultiple", SelectMultiple),
        ("select", Select),
    ):
        if isinstance(widget, cls):
            return kind
    return "text"


def _value(bound, kind):
    value = bound.value()
    if kind == "checkbox":
        return bool(value)
    if kind == "selectmultiple":
        return [str(item) for item in (value or [])]
    if kind == "select":
        return "" if value in (None, "") else str(value)
    formatted = bound.field.widget.format_value(value)
    return "" if formatted is None else str(formatted)


def _campo(bound):
    field = bound.field
    kind = _widget(field.widget)
    campo = {
        "name": bound.name,
        "label": str(bound.label),
        "required": field.required,
        "disabled": field.disabled,
        "widget": kind,
        "help_text": str(field.help_text),
        "value": _value(bound, kind),
        "attrs": {
            key: str(value)
            for key, value in field.widget.attrs.items()
            if key not in ("class", "type")
        },
    }
    if kind in ("select", "selectmultiple"):
        campo["choices"] = _choices(field.choices)
    return campo


def _form_body(request, form, titulo):
    return {
        "titulo": titulo,
        "fields": [_campo(bound) for bound in form],
        "errors": form.errors.get_json_data() if form.is_bound else {},
        "non_field_errors": [str(e) for e in form.non_field_errors()],
        "can_add_dispositivo": request.user.has_perm("dispositivos.add_dispositivo"),
        "urls": {
            "cancel": reverse("datacalle_relevamientos_listar"),
            "add_dispositivo": reverse("dispositivos_crear"),
            "municipios": reverse("ajax_load_municipios"),
            "localidades": reverse("ajax_load_localidades"),
            "dispositivos": reverse("web_datacalle_opciones_dispositivos"),
            "relevadores": reverse("web_datacalle_opciones_relevadores"),
        },
        "messages": pending_messages(request),
    }


def _create_view(request):
    vista = native_view(RelevamientoCreateView, request)
    vista.object = None
    return vista


def _save(request, vista, status):
    """Run the native ``form_valid`` (``save_relevamiento_from_form``) or answer 400."""
    form = vista.get_form()
    if not form.is_valid():
        return Response(
            _form_body(request, form, vista.get_context_data(form=form)["titulo"]),
            status=400,
        )
    vista.form_valid(form)
    return Response(
        {"id": str(vista.object.pk), "url": vista.get_success_url()}, status=status
    )


class RelevamientoCreateFormWebView(DataCalleWebView):
    """``GET relevamientos/formulario/``: the empty create form."""

    permission_classes = [WebGatePermission, ADD]

    def get(self, request):
        vista = _create_view(request)
        form = vista.get_form()
        return Response(
            _form_body(request, form, vista.get_context_data(form=form)["titulo"])
        )


class RelevamientoCreateWebView(DataCalleWebView):
    """``POST relevamientos/crear/``: 201 with the native ficha URL, or 400."""

    permission_classes = [WebGatePermission, ADD]
    http_method_names = ["post"]

    def post(self, request):
        return _save(request, _create_view(request), 201)


class RelevamientoUpdateFormWebView(DataCalleWebView):
    """``GET relevamientos/<uuid>/formulario/``: the form with the saved values."""

    permission_classes = [WebGatePermission, CHANGE]

    def get(self, request, pk):
        vista = _native_object(RelevamientoUpdateView, request, pk)
        form = vista.get_form()
        return Response(
            _form_body(request, form, vista.get_context_data(form=form)["titulo"])
        )


class RelevamientoUpdateWebView(DataCalleWebView):
    """``POST relevamientos/<uuid>/editar/``: 200 with the ficha URL, or 400."""

    permission_classes = [WebGatePermission, CHANGE]
    http_method_names = ["post"]

    def post(self, request, pk):
        return _save(request, _native_object(RelevamientoUpdateView, request, pk), 200)


class RelevamientoDeleteWebView(DataCalleWebView):
    """``GET``: the confirmation; ``POST``: the native soft delete, no message."""

    permission_classes = [WebGatePermission, DELETE]
    http_method_names = ["get", "head", "post"]

    def get(self, request, pk):
        relevamiento = _native_object(RelevamientoDeleteView, request, pk).object
        return Response(
            {
                "id": str(relevamiento.pk),
                "denominacion": relevamiento.denominacion,
                "urls": {"cancel": _detail_url(relevamiento.pk)},
                "messages": pending_messages(request),
            }
        )

    def post(self, request, pk):
        vista = _native_object(RelevamientoDeleteView, request, pk)
        vista.form_valid(vista.get_form())
        return Response({"url": str(vista.success_url)})


# --- DC01.03 close -----------------------------------------------------------


class RelevamientoCerrarWebView(DataCalleWebView):
    """``POST relevamientos/<uuid>/cerrar/``: idempotent, never a 409."""

    permission_classes = [WebGatePermission, CHANGE]
    http_method_names = ["post"]

    def post(self, request, pk):
        relevamiento = _native_object(RelevamientoCerrarView, request, pk).object
        _, cerrado_ahora = cerrar_relevamiento(
            relevamiento=relevamiento, user=request.user
        )
        # Same queued message as the native view: the ficha shows it once.
        if cerrado_ahora:
            messages.success(_django(request), CERRADO)
        else:
            messages.info(_django(request), YA_CERRADO)
        return Response(
            {
                "cerrado_ahora": cerrado_ahora,
                "message": CERRADO if cerrado_ahora else YA_CERRADO,
                "level": "success" if cerrado_ahora else "info",
                "url": _detail_url(relevamiento.pk),
            }
        )


# --- Lookups of the form cascade --------------------------------------------


class DispositivosOpcionesWebView(DataCalleWebView):
    """``GET opciones/dispositivos/?provincia_id=``: the native AJAX body."""

    def get(self, request):
        return cargar_dispositivos(_django(request))


class RelevadoresOpcionesWebView(DataCalleWebView):
    """``GET opciones/relevadores/?provincia_id=``: the native AJAX body."""

    def get(self, request):
        return cargar_relevadores(_django(request))
