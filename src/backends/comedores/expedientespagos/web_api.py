"""Web API (G1 v1) of the payment files of a comedor (EX01.01 and EX01.02).

``/api/web/comedores/`` is published by the Comedores backend (``url_prefixes``
in ``src/backends/config/backends.json``). In a split deploy the core checks the
session and the web prerequisites and signs each request; the runtime only
serves requests its ``WebGateMiddleware`` verified. In the monolith
``WebGatePermission`` evaluates the same policy locally. After that the native
rules apply unchanged (kept on purpose, see
``docs/registro/decisiones/2026-11-10-2785-brechas-acceso-conservadas.md``):

- list and detail: any authenticated user, no action permission, no scope;
- create, edit and delete: ``permissions_any_required`` with the four read codes
  of ``expedientespagos/urls.py`` (superuser included), on GET and POST.

Every endpoint runs the native view of ``expedientespagos.views``: its queryset
and the global paginator (invalid ``page`` 404), the column preferences, the
role flags of the form, ``ExpedientesPagosService.crear_expediente_pago``
followed by the native ``form_valid`` (which saves the form again, so a valid
create stores a second row without comedor, exactly as today), the native
``form_valid`` of the edit and the logical delete with its message. Values are
rendered with the template filters of the HTML pages, so React never formats
money or recomputes totals.

Two transport decisions of the EX01 contract: only the 23 rendered fields reach
the form (``deleted_at``, ``deleted_by``, ``comedor`` and ``mes_convenio`` are
never read from the request), and a create for a comedor that does not exist
answers 404 JSON instead of the native 500. The native views stay as they are.
"""

from html import unescape

from django import forms
from django.contrib import messages
from django.http import Http404, QueryDict
from django.template import Context, Template
from django.urls import reverse
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import NotFound
from rest_framework.permissions import BasePermission
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.views import APIView

# The exact predicate of the native URL decorator.
from core.decorators import _has_any_permissions
from core.templatetags.custom_filters import has_any_perm
from core.web_gate import WebGatePermission
from comedores.models import Comedor
from expedientespagos.services import ExpedientesPagosService
from expedientespagos.views import (
    ExpedientesPagosCreateView,
    ExpedientesPagosDeleteView,
    ExpedientesPagosDetailView,
    ExpedientesPagosListView,
    ExpedientesPagosUpdateView,
)

# ``expedientespagos/urls.py`` (operations) and ``expedientespagos_list.html``
# («Nuevo Expediente de Pago»): the same four read codes.
OPERATION_PERMISSIONS = [
    "comedores.view_comedor",
    "admisiones.view_admision",
    "acompanamientos.view_informacionrelevante",
    "expedientespagos.view_expedientepago",
]
# ``expedientespagos_form.html``: the fields the page renders, in order.
FORM_FIELDS = (
    "expediente_pago",
    "expediente_convenio",
    "anexo",
    "if_cantidad_de_prestaciones",
    "if_pagado",
    "total_prestaciones",
    "gastos_accesorios",
    "total",
    "mes_pago",
    "ano",
    "organizacion_creacion",
    "numero_orden_pago",
    "fecha_pago_al_banco",
    "fecha_acreditacion",
    "observaciones",
    "prestaciones_mensuales_desayuno",
    "prestaciones_mensuales_almuerzo",
    "prestaciones_mensuales_merienda",
    "prestaciones_mensuales_cena",
    "monto_mensual_desayuno",
    "monto_mensual_almuerzo",
    "monto_mensual_merienda",
    "monto_mensual_cena",
)
DELETE_MESSAGE = "¿Estás seguro que deseas dar de baja lógica el expediente"
MESSAGE_LEVELS = {
    messages.DEBUG: "info",
    messages.INFO: "info",
    messages.SUCCESS: "success",
    messages.WARNING: "warning",
    messages.ERROR: "error",
}
# ``expedientespagos_detail.html``, value by value.
_DETAIL = {
    "expediente_pago": '{{ e.expediente_pago|default:"-" }}',
    "expediente_convenio": '{{ e.expediente_convenio|default:"-" }}',
    "mes_pago": '{{ e.mes_pago|default:"-" }}',
    "mes_convenio": '{{ e.mes_convenio|default:"-" }}',
    "ano": '{{ e.ano|default:"-" }}',
    "organizacion_creacion": '{{ e.organizacion_creacion|default:"-" }}',
    "anexo": '{{ e.anexo|default:"-" }}',
    "total_prestaciones": "${{ e.total_prestaciones|monto_sin_decimales }}",
    "gastos_accesorios": "${{ e.gastos_accesorios|monto_sin_decimales }}",
    "total": "${{ e.total|monto_sin_decimales }}",
    "numero_orden_pago": '{{ e.numero_orden_pago|default:"-" }}',
    "fecha_creacion": '{{ e.fecha_creacion|date:"d/m/Y" }}',
    "fecha_pago_al_banco": '{{ e.fecha_pago_al_banco|date:"d/m/Y"|default:"-" }}',
    "fecha_acreditacion": '{{ e.fecha_acreditacion|date:"d/m/Y"|default:"-" }}',
    "observaciones": "{% if e.observaciones %}{{ e.observaciones }}{% endif %}",
    **{
        f"prestaciones_mensuales_{comida}": (
            f'{{{{ e.prestaciones_mensuales_{comida}|default:"-" }}}}'
        )
        for comida in ("desayuno", "almuerzo", "merienda", "cena")
    },
    **{
        f"monto_mensual_{comida}": (
            f"${{{{ e.monto_mensual_{comida}|monto_sin_decimales }}}}"
        )
        for comida in ("desayuno", "almuerzo", "merienda", "cena")
    },
}
_DETAIL_TEMPLATES = {
    key: Template("{% load custom_filters %}" + source)
    for key, source in _DETAIL.items()
}
_UPPER = Template("{{ valor|upper }}")


class ExpedienteOperation(BasePermission):
    """The native route decorator of create, edit and delete, unchanged."""

    def has_permission(self, request, view):
        return _has_any_permissions(request.user, OPERATION_PERMISSIONS)


class _WebView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [WebGatePermission]
    renderer_classes = [JSONRenderer]
    http_method_names = ["get", "head"]
    native_class = None

    def native(self, **kwargs):
        vista = self.native_class()  # pylint: disable=not-callable
        vista.setup(self.request._request, **kwargs)  # pylint: disable=protected-access
        return vista


def _render(template, **context):
    return unescape(template.render(Context(context)).strip())


def _pending_messages(request):
    return [
        {"message": str(m), "level": MESSAGE_LEVELS.get(m.level, "info")}
        for m in messages.get_messages(request)
    ]


class ExpedientesListWebView(_WebView):
    """``GET .../expedientespagos/comedores/<comedor_id>/``: ``expedientespagos_list.html``."""

    native_class = ExpedientesPagosListView

    def get(self, request, comedor_id):
        vista = self.native(pk=comedor_id)
        try:
            vista.object_list = vista.get_queryset()
            # The unused global paginator: an invalid ``page`` is the native 404.
            context = vista.get_context_data()
        except Http404 as exc:
            raise NotFound() from exc
        return Response(
            {
                "comedor_id": comedor_id,
                "can_create": has_any_perm(
                    request.user, ",".join(OPERATION_PERMISSIONS)
                ),
                "create_url": reverse("expedientespagos_create", args=[comedor_id]),
                "breadcrumb_url": reverse(
                    "detalle_acompanamiento", kwargs={"comedor_id": comedor_id}
                ),
                "columns": context["column_config"],
                "headers": [str(h["title"]) for h in context["table_headers"]],
                "results": [
                    {
                        "id": item["pk"],
                        "cells": [unescape(str(c["content"])) for c in item["cells"]],
                        "detail_url": reverse(
                            "expedientespagos_detail", args=[item["pk"]]
                        ),
                    }
                    for item in context["expedientes_pagos"]
                ],
                "messages": _pending_messages(request),
            }
        )


class ExpedienteDetailWebView(_WebView):
    """``GET .../expedientespagos/<pk>/``: ``expedientespagos_detail.html``."""

    native_class = ExpedientesPagosDetailView

    def get(self, request, pk):
        vista = self.native(pk=pk)
        try:
            vista.object = vista.get_object()
        except Http404 as exc:
            raise NotFound() from exc
        expediente = vista.get_context_data(object=vista.object)["expediente"]
        return Response(
            {
                "id": expediente.pk,
                "comedor_id": expediente.comedor_id,
                "expediente": {
                    key: _render(template, e=expediente)
                    for key, template in _DETAIL_TEMPLATES.items()
                },
                # The native ``{% url %}`` fails the same way without comedor.
                "list_url": reverse(
                    "expedientespagos_list", args=[expediente.comedor_id]
                ),
                "update_url": reverse("expedientespagos_update", args=[expediente.pk]),
                "delete_url": reverse("expedientespagos_delete", args=[expediente.pk]),
                "messages": _pending_messages(request),
            }
        )


def _field_type(widget):
    if isinstance(widget, forms.Textarea):
        return "textarea"
    return widget.input_type


def _fields(form):
    """The 23 rendered fields as crispy renders them (attributes, value, errors)."""
    campos = []
    for name in FORM_FIELDS:
        bound = form[name]
        widget = bound.field.widget
        attrs = bound.build_widget_attrs(dict(widget.attrs))
        valor = widget.format_value(bound.value())
        campos.append(
            {
                "name": name,
                "label": str(bound.label),
                "type": _field_type(widget),
                "required": bool(bound.field.required),
                "max_length": attrs.get("maxlength"),
                "step": attrs.get("step"),
                "value": "" if valor is None else str(valor),
                "errors": [str(error) for error in bound.errors],
            }
        )
    return campos


def _whitelisted(request):
    """Only the rendered fields reach the form."""
    datos = QueryDict(mutable=True)
    for name in FORM_FIELDS:
        if name in request.POST:
            datos.setlist(name, request.POST.getlist(name))
    return datos


def _bound_form(vista, request):
    kwargs = vista.get_form_kwargs()
    kwargs["data"] = _whitelisted(request)
    kwargs.pop("files", None)
    return vista.get_form_class()(**kwargs)


def _errors(form):
    return form.errors.get_json_data()


class ExpedienteCreateWebView(_WebView):
    """``.../expedientespagos/comedores/<comedor_id>/crear/``: the native create."""

    permission_classes = [WebGatePermission, ExpedienteOperation]
    http_method_names = ["get", "head", "post"]
    native_class = ExpedientesPagosCreateView

    def preparar(self, comedor_id):
        vista = self.native(pk=comedor_id)
        vista.object = None
        return vista

    @staticmethod
    def payload(vista, comedor_id):
        # ``get_context_data`` always replaces the form by an unbound one
        # without role flags: that is what the native page shows.
        context = vista.get_context_data()
        return {
            "comedor_id": comedor_id,
            "fields": _fields(context["form"]),
            "cancel_url": context["expedientes_list_url"],
        }

    def get(self, request, comedor_id):
        vista = self.preparar(comedor_id)
        return Response(self.payload(vista, comedor_id))

    def post(self, request, comedor_id):
        vista = self.preparar(comedor_id)
        form = _bound_form(vista, request)
        comedor = Comedor.objects.filter(pk=comedor_id).first()
        if comedor is None:
            raise NotFound()
        if not form.is_valid():
            return Response(
                {
                    **self.payload(vista, comedor_id),
                    "errors": _errors(form),
                    "reset_form": True,
                },
                status=400,
            )
        vista.object = ExpedientesPagosService.crear_expediente_pago(
            comedor, form.cleaned_data
        )
        respuesta = vista.form_valid(form)
        return Response({"ok": True, "redirect": respuesta["Location"]})


class ExpedienteUpdateWebView(_WebView):
    """``.../expedientespagos/<pk>/editar/``: the native edit with role flags."""

    permission_classes = [WebGatePermission, ExpedienteOperation]
    http_method_names = ["get", "head", "post"]
    native_class = ExpedientesPagosUpdateView

    def preparar(self, pk):
        vista = self.native(pk=pk)
        try:
            vista.object = vista.get_object()
        except Http404 as exc:
            raise NotFound() from exc
        return vista

    @staticmethod
    def payload(vista, form):
        context = vista.get_context_data(form=form)
        return {
            "id": vista.object.pk,
            "comedor_id": context["comedorid"],
            "fields": _fields(form),
            "cancel_url": context["expedientes_list_url"],
            "errors": _errors(form) if form.is_bound else {},
        }

    def get(self, request, pk):
        vista = self.preparar(pk)
        return Response(self.payload(vista, vista.get_form()))

    def post(self, request, pk):
        vista = self.preparar(pk)
        form = _bound_form(vista, request)
        if not form.is_valid():
            return Response(self.payload(vista, form), status=400)
        respuesta = vista.form_valid(form)
        return Response({"ok": True, "redirect": respuesta["Location"]})


def _cascade(preview):
    if not preview:
        return None
    return {
        "total_afectados": preview.get("total_afectados", 0),
        "total_baja_logica": preview.get("total_baja_logica", 0),
        "total_borrado_fisico": preview.get("total_borrado_fisico", 0),
        "desglose_por_modelo": [
            {
                "modelo": str(item.get("modelo", "")),
                "cantidad": item.get("cantidad", 0),
                "modo": item.get("modo", ""),
                "ejemplos": [str(ejemplo) for ejemplo in item.get("ejemplos") or []],
            }
            for item in preview.get("desglose_por_modelo", [])
        ],
    }


class ExpedienteDeleteWebView(_WebView):
    """``.../expedientespagos/<pk>/eliminar/``: confirmation and logical delete."""

    permission_classes = [WebGatePermission, ExpedienteOperation]
    http_method_names = ["get", "head", "post"]
    native_class = ExpedientesPagosDeleteView

    def preparar(self, pk):
        vista = self.native(pk=pk)
        try:
            vista.object = vista.get_object()
        except Http404 as exc:
            raise NotFound() from exc
        return vista

    def get(self, request, pk):
        vista = self.preparar(pk)
        context = vista.get_context_data()
        objeto = vista.object
        return Response(
            {
                "id": objeto.pk,
                "expediente_pago": _render(_UPPER, valor=objeto.expediente_pago),
                "breadcrumb_label": _render(
                    Template("{{ valor }}"), valor=objeto.expediente_pago
                ),
                "message": DELETE_MESSAGE,
                "cascade_preview": _cascade(context.get("cascade_preview")),
                "cancel_url": reverse("expedientespagos_detail", args=[objeto.pk]),
            }
        )

    def post(self, request, pk):
        vista = self.preparar(pk)
        respuesta = vista.form_valid(vista.get_form())
        return Response(
            {
                "ok": True,
                "message": vista.success_message,
                "redirect": respuesta["Location"],
            }
        )
