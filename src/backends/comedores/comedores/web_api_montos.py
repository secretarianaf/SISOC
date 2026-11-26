"""Web API (G1 v1) of the amounts-per-program ABM (``montoprestacion/``, CO05).

``/api/web/comedores/`` is published by the Comedores backend (``url_prefixes``
in ``src/backends/config/backends.json``). In a split deploy the core checks the
session and the web prerequisites and signs each request; the runtime only
serves requests its ``WebGateMiddleware`` verified. In the monolith
``WebGatePermission`` evaluates the same policy locally. After that the native
rule applies unchanged: ``permissions_any_required(GRUPOS_MONTO_PRESTACION)``.

Every endpoint runs the native view itself (``views.montos_prestacion``): its
queryset, 10 per page, invalid page 404, form, transactional history,
``usuario_creador`` assignment, success messages and the physical ``DeleteView``
removal. This module only projects their context to JSON and turns the native
redirect into ``{"ok": true, "redirect": <url>}``. Values are rendered with the
Django template engine, so the text matches the HTML page (``None``, decimal
comma, ``d/m/Y H:i``).
"""

from html import unescape

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.template import Context, Template
from django.urls import reverse
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import NotFound
from rest_framework.permissions import BasePermission
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.views import APIView

from core.decorators import permissions_any_required
from core.pagination import build_compact_page_range
from core.web_gate import WebGatePermission
from comedores.montos_urls import GRUPOS_MONTO_PRESTACION
from comedores.views.montos_prestacion import (
    MontoPrestacionProgramaCreateView,
    MontoPrestacionProgramaDeleteView,
    MontoPrestacionProgramaDetailView,
    MontoPrestacionProgramaListView,
    MontoPrestacionProgramaUpdateView,
)

VALORES = ("desayuno_valor", "almuerzo_valor", "merienda_valor", "cena_valor")
_VALOR = Template("{{ valor }}")
_FECHA = Template("{{ valor|date:'d/m/Y H:i' }}")
_MAYUSCULAS = Template("{{ valor|upper }}")
_NIVELES = {
    messages.ERROR: "error",
    messages.WARNING: "warning",
    messages.SUCCESS: "success",
}

# Same check the native routes run (``montos_urls``): any of the listed codes.
_regla_nativa = permissions_any_required(GRUPOS_MONTO_PRESTACION)(lambda request: True)


class GrupoMontoPrestacion(BasePermission):
    """The native route decorator, unchanged: only what it admits passes."""

    def has_permission(self, request, view):
        try:
            return _regla_nativa(request._request)  # pylint: disable=protected-access
        except PermissionDenied:
            return False


class _WebView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [WebGatePermission, GrupoMontoPrestacion]
    renderer_classes = [JSONRenderer]
    native_class = None

    def native(self, **kwargs):
        vista = self.native_class()  # pylint: disable=not-callable
        vista.setup(self.request._request, **kwargs)  # pylint: disable=protected-access
        return vista


def _texto(valor, plantilla=_VALOR):
    return unescape(plantilla.render(Context({"valor": valor})))


def _monto(monto):
    return {
        "id": monto.pk,
        "programa": _texto(monto.programa),
        **{campo: _texto(getattr(monto, campo)) for campo in VALORES},
        "usuario_creador": _texto(monto.usuario_creador),
        "fecha_creacion": _texto(monto.fecha_creacion, _FECHA),
        "fecha_modificacion": _texto(monto.fecha_modificacion, _FECHA),
    }


def _mensajes(request):
    return [
        {"message": str(mensaje), "level": _NIVELES.get(mensaje.level, "info")}
        for mensaje in messages.get_messages(request)
    ]


def _migas(items):
    return [
        {
            "text": str(item["text"]),
            "url": item.get("url") if not item.get("active") else None,
        }
        for item in items
    ]


def _consulta_sin_pagina(request):
    """Prefix the native pagination links repeat (``components/pagination.html``)."""
    filtro = Template(
        "{% for key, value in request.GET.items %}{% if key != 'page' and "
        "key != 'busqueda' %}{{ key }}={{ value|urlencode }}&{% endif %}{% endfor %}"
    )
    return unescape(filtro.render(Context({"request": request})))


def _pagina(context, request):
    page = context["page_obj"]
    return {
        "number": page.number,
        "count": page.paginator.count,
        "is_paginated": bool(context["is_paginated"]),
        "previous": page.previous_page_number() if page.has_previous() else None,
        "next": page.next_page_number() if page.has_next() else None,
        "range": [
            "…" if numero in ("...", "…") else numero
            for numero in build_compact_page_range(page)
        ],
        "query_without_page": _consulta_sin_pagina(request),
    }


def _valor_de_campo(campo):
    """The ``value`` attribute the native widget renders (Select: chosen pk)."""
    valor = campo.field.widget.format_value(campo.value())
    if isinstance(valor, list):
        return valor[0] if valor else ""
    return "" if valor is None else str(valor)


def _redireccion(respuesta):
    return Response({"ok": True, "redirect": respuesta["Location"]})


class MontosListWebView(_WebView):
    """``GET /api/web/comedores/montos/``: the native list, 10 per page."""

    http_method_names = ["get", "head"]
    native_class = MontoPrestacionProgramaListView

    def get(self, request):
        vista = self.native()
        try:
            vista.object_list = vista.get_queryset()
            context = vista.get_context_data()
        except Http404 as exc:
            raise NotFound() from exc
        django_request = request._request  # pylint: disable=protected-access
        return Response(
            {
                "results": [_monto(monto) for monto in context["prestaciones"]],
                "page": _pagina(context, django_request),
                "urls": {
                    "listar": reverse("montoprestacion_listar"),
                    "crear": reverse("montoprestacion_crear"),
                },
                "messages": _mensajes(django_request),
            }
        )


class MontoDetailWebView(_WebView):
    """``GET /api/web/comedores/montos/<pk>/``: the native detail table."""

    http_method_names = ["get", "head"]
    native_class = MontoPrestacionProgramaDetailView

    def get(self, request, pk):
        vista = self.native(pk=pk)
        try:
            vista.object = vista.get_object()
        except Http404 as exc:
            raise NotFound() from exc
        context = vista.get_context_data(object=vista.object)
        return Response(
            {
                "breadcrumb": _migas(context["breadcrumb_items"]),
                "back_button": context["back_button"],
                "monto": _monto(vista.object),
            }
        )


class _FormWebView(_WebView):
    """Native ``form_valid`` (history, creator, message) or the bound form, 400."""

    http_method_names = ["get", "head", "post"]

    def objeto(self, vista):
        raise NotImplementedError

    def preparar(self, kwargs):
        vista = self.native(**kwargs)
        try:
            vista.object = self.objeto(vista)
        except Http404 as exc:
            raise NotFound() from exc
        return vista

    def get(self, request, **kwargs):
        vista = self.preparar(kwargs)
        return self.formulario(vista, vista.get_form())

    def post(self, request, **kwargs):
        vista = self.preparar(kwargs)
        form = vista.get_form()
        if form.is_valid():
            return _redireccion(vista.form_valid(form))
        return self.formulario(vista, form, status=400)

    @staticmethod
    def formulario(vista, form, status=200):
        context = vista.get_context_data(form=form)
        programa = form.fields["programa"]
        campos = [
            {
                "name": nombre,
                "label": str(campo.label),
                "required": campo.required,
                "value": _valor_de_campo(form[nombre]),
            }
            for nombre, campo in form.fields.items()
        ]
        campos[0]["choices"] = [
            {"value": str(valor), "label": str(etiqueta)}
            for valor, etiqueta in programa.choices
        ]
        return Response(
            {
                "breadcrumb": _migas(context["breadcrumb_items"]),
                "back_button": context["back_button"],
                "fields": campos,
                "errors": form.errors.get_json_data() if form.is_bound else {},
            },
            status=status,
        )


class MontoCreateWebView(_FormWebView):
    """``/api/web/comedores/montos/crear/``: GET the empty form, POST to create."""

    native_class = MontoPrestacionProgramaCreateView

    def objeto(self, vista):
        return None


class MontoUpdateWebView(_FormWebView):
    """``/api/web/comedores/montos/<pk>/editar/``: GET the bound form, POST to save."""

    native_class = MontoPrestacionProgramaUpdateView

    def objeto(self, vista):
        return vista.get_object()


class MontoDeleteWebView(_WebView):
    """``/api/web/comedores/montos/<pk>/eliminar/``: native confirmation and removal.

    POST runs the native ``DeleteView.form_valid``: history first, then the
    physical delete, both in one transaction, and the success message.
    """

    http_method_names = ["get", "head", "post"]
    native_class = MontoPrestacionProgramaDeleteView

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
        return Response(
            {
                "breadcrumb": _migas(context["breadcrumb_items"]),
                "object_name": _texto(context["object_title"], _MAYUSCULAS),
                "delete_message": context["delete_message"],
                "cancel_url": context["cancel_url"],
            }
        )

    def post(self, request, pk):
        vista = self.preparar(pk)
        return _redireccion(vista.form_valid(vista.get_form()))
