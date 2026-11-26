"""Web API (G1 v1) of the global PNUD activity catalog (CO04.02).

Same G1 order as ``web_api_montos``: the gate first, then the native rule of
``views.actividades_pnud`` itself (``ActividadPnudPermissionMixin``: ``role_admin``
or the view/manage codes to read, ``role_admin`` or manage to write). Every
endpoint runs the native view: 50 per page ordered by categoria, actividad, id,
the ``estado``/``q`` filters, ``ActividadPnudForm`` with ``categoria_modo``,
the success messages and the deactivation (``activo=False`` and
``fecha_actualizacion``, never a delete). This module only projects their
context to JSON.
"""

from django.http import Http404
from django.urls import reverse
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import NotFound
from rest_framework.permissions import BasePermission
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.views import APIView

from core.web_gate import WebGatePermission
from comedores.views.actividades_pnud import (
    ActividadPnudCreateView,
    ActividadPnudDeactivateView,
    ActividadPnudListView,
    ActividadPnudUpdateView,
)
from comedores.web_api_montos import (
    _mensajes,
    _pagina,
    _redireccion,
    _valor_de_campo,
)


class ReglaNativa(BasePermission):
    """The ``test_func`` of the native view's permission mixin, unchanged."""

    def has_permission(self, request, view):
        return view.native().test_func()


class _WebView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [WebGatePermission, ReglaNativa]
    renderer_classes = [JSONRenderer]
    native_class = None

    def native(self, **kwargs):
        vista = self.native_class()  # pylint: disable=not-callable
        vista.setup(self.request._request, **kwargs)  # pylint: disable=protected-access
        return vista

    def objeto(self, vista):
        try:
            return vista.get_object()
        except Http404 as exc:
            raise NotFound() from exc


def _actividad(actividad):
    return {
        "id": actividad.pk,
        "categoria": actividad.categoria,
        "actividad": actividad.actividad,
        "activo": actividad.activo,
    }


class ActividadesListWebView(_WebView):
    """``GET /api/web/comedores/actividades-pnud/``: the native list and filters."""

    http_method_names = ["get", "head"]
    native_class = ActividadPnudListView

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
                "results": [_actividad(a) for a in context["actividades"]],
                "estado": context["estado_filtro"],
                "q": context["busqueda"],
                "can_manage": context["can_manage_actividades_pnud"],
                "page": _pagina(context, django_request),
                "messages": _mensajes(django_request),
            }
        )


class _FormWebView(_WebView):
    """Native ``form_valid`` (message, redirect) or the bound form with 400."""

    http_method_names = ["get", "head", "post"]
    editar = False

    def preparar(self, kwargs):
        vista = self.native(**kwargs)
        vista.object = self.objeto(vista) if self.editar else None
        return vista

    def get(self, request, **kwargs):
        vista = self.preparar(kwargs)
        return self.formulario(vista.get_form())

    def post(self, request, **kwargs):
        vista = self.preparar(kwargs)
        form = vista.get_form()
        if form.is_valid():
            return _redireccion(vista.form_valid(form))
        return self.formulario(form, status=400)

    def formulario(self, form, status=200):
        def campo(nombre):
            return form[nombre]

        existente = form.fields["categoria_existente"]
        actividad = form.fields["actividad"]
        return Response(
            {
                "editar": self.editar,
                "values": {
                    "categoria": _valor_de_campo(campo("categoria")),
                    "categoria_modo": _valor_de_campo(campo("categoria_modo"))
                    or "existente",
                    "categoria_existente": _valor_de_campo(
                        campo("categoria_existente")
                    ),
                    "categoria_nueva": _valor_de_campo(campo("categoria_nueva")),
                    "actividad": _valor_de_campo(campo("actividad")),
                    "activo": bool(campo("activo").value()),
                },
                "categorias": [
                    {"value": str(valor), "label": str(etiqueta)}
                    for valor, etiqueta in existente.choices
                ],
                "actividad_max_length": actividad.max_length,
                "errors": form.errors.get_json_data() if form.is_bound else {},
                "list_url": reverse("actividades_pnud_list"),
            },
            status=status,
        )


class ActividadCreateWebView(_FormWebView):
    """``/api/web/comedores/actividades-pnud/crear/``."""

    native_class = ActividadPnudCreateView


class ActividadUpdateWebView(_FormWebView):
    """``/api/web/comedores/actividades-pnud/<pk>/editar/``."""

    native_class = ActividadPnudUpdateView
    editar = True


class ActividadDeactivateWebView(_WebView):
    """``/api/web/comedores/actividades-pnud/<pk>/baja/``: confirmation and native POST.

    The native POST marks ``activo=False`` (``fecha_actualizacion`` with it) or,
    when it already was inactive, only leaves its info message.
    """

    http_method_names = ["get", "head", "post"]
    native_class = ActividadPnudDeactivateView

    def get(self, request, pk):
        vista = self.native(pk=pk)
        actividad = self.objeto(vista)
        return Response(
            {
                "categoria": actividad.categoria,
                "actividad": actividad.actividad,
                "cancel_url": reverse("actividades_pnud_list"),
            }
        )

    def post(self, request, pk):
        vista = self.native(pk=pk)
        self.objeto(vista)
        return _redireccion(vista.post(vista.request, pk=pk))
