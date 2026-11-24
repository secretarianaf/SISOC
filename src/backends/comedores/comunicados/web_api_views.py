"""Web API (G1 v1) of the comunicados pages served by React (CM03.01, CM02.01).

``/api/web/comedores/`` is published by the Comedores backend (``url_prefixes``
in ``src/backends/config/backends.json``). In a split deploy the core checks the
session and the web prerequisites and signs each request; the runtime only
serves requests its ``WebGateMiddleware`` verified. In the monolith
``WebGatePermission`` evaluates the same policy locally. After that the native
rule applies unchanged: any signed-in user reads (``LoginRequiredMixin``).

Each endpoint runs the native view itself (queryset, filters, paginator and
its 404, context); this module only projects that context to JSON. This is
not the PWA API (``comunicados.api_views``), which stays untouched.
"""

from django.http import Http404
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.views import APIView

from comunicados.permissions import (
    can_delete_comunicado,
    can_manage_comunicados,
    require_create_permission,
    require_edit_permission,
)
from comunicados.views import (
    ComunicadoArchivarView,
    ComunicadoCreateView,
    ComunicadoDeleteView,
    ComunicadoDetailView,
    ComunicadoGestionListView,
    ComunicadoListView,
    ComunicadoPublicarView,
    ComunicadoToggleDestacadoView,
    ComunicadoUpdateView,
    DestinatariosBuscarView,
    DestinatariosSeleccionarTodosView,
)
from comunicados.web_api_serializers import (
    detalle,
    eliminar_confirmacion,
    formulario,
    fila_gestion,
    pagina,
    pending_messages,
    tarjeta_publicada,
)
from core.web_gate import WebGatePermission


class _NativeReadView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [WebGatePermission]
    renderer_classes = [JSONRenderer]
    http_method_names = ["get", "head"]

    @staticmethod
    def native(view_class, request, **kwargs):
        vista = view_class()
        vista.setup(request._request, **kwargs)  # pylint: disable=protected-access
        return vista


class ComunicadoListWebView(_NativeReadView):
    """``GET .../comunicados/``: ``comunicado_list.html`` (published internal ones)."""

    def get(self, request):
        vista = self.native(ComunicadoListView, request)
        vista.object_list = vista.get_queryset()
        try:
            context = vista.get_context_data()
        except Http404 as exc:
            raise NotFound("Página no válida.") from exc
        can_manage = context["can_manage"]
        return Response(
            {
                "results": [tarjeta_publicada(c) for c in context["comunicados"]],
                "page": pagina(context, request),
                "filtro_titulo": context["filtro_titulo"],
                "can_manage": can_manage,
                "gestion_url": (
                    context["additional_buttons"][0]["url"] if can_manage else None
                ),
                "messages": pending_messages(request),
            }
        )


class ComunicadoGestionWebView(_NativeReadView):
    """``GET .../comunicados/gestion/``: ``comunicado_gestion_list.html`` (CM02.01)."""

    def get(self, request):
        # ``ComunicadoGestionListView.dispatch``: same check and message.
        if not can_manage_comunicados(request.user):
            raise PermissionDenied("No tiene permisos para gestionar comunicados.")
        vista = self.native(ComunicadoGestionListView, request)
        vista.object_list = vista.get_queryset()
        try:
            context = vista.get_context_data()
        except Http404 as exc:
            raise NotFound("Página no válida.") from exc
        return Response(
            {
                "results": [fila_gestion(c, context) for c in context["comunicados"]],
                "page": pagina(context, request),
                "filtros": {
                    "titulo": context["filtro_titulo"],
                    "estado": context["filtro_estado"],
                    "tipo": context["filtro_tipo"],
                },
                "flags": {
                    "can_create": context["can_create"],
                    "is_admin": context["is_admin"],
                    "es_tecnico": context["es_tecnico"],
                },
                "mailing_url": (
                    context["additional_buttons"][0]["url"]
                    if context["is_admin"]
                    else None
                ),
                "messages": pending_messages(request),
            }
        )


class ComunicadoDetailWebView(_NativeReadView):
    """``GET .../comunicados/<pk>/``: ``comunicado_detail.html`` with its native queryset."""

    def get(self, request, pk):
        vista = self.native(ComunicadoDetailView, request, pk=pk)
        try:
            vista.object = vista.get_object()
        except Http404 as exc:
            raise NotFound() from exc
        context = vista.get_context_data(object=vista.object)
        return Response(
            {
                **detalle(vista.object, context),
                "messages": pending_messages(request),
            }
        )


class _NativeActionView(_NativeReadView):
    """CM02.03: runs the native ``post()`` of a state-transition view.

    The native view checks its permission first (so an unknown id is 403, not
    404 without permission), then looks the object up, applies the transition
    and queues its message. The 302 to ``comunicados_gestion`` becomes
    ``{"ok": true, "redirect": ...}`` and the next GET consumes the message.
    """

    http_method_names = ["post"]
    view_class = None

    def post(self, request, pk):
        vista = self.native(self.view_class, request, pk=pk)
        try:
            # pylint: disable-next=protected-access
            respuesta = vista.post(request._request, pk=pk)
        except Http404 as exc:
            raise NotFound() from exc
        return Response({"ok": True, "redirect": respuesta["Location"]})


class ComunicadoPublicarWebView(_NativeActionView):
    """``POST .../comunicados/<pk>/publicar/``: ``ComunicadoPublicarView``."""

    view_class = ComunicadoPublicarView


class ComunicadoArchivarWebView(_NativeActionView):
    """``POST .../comunicados/<pk>/archivar/``: ``ComunicadoArchivarView``."""

    view_class = ComunicadoArchivarView


class ComunicadoDestacadoWebView(_NativeActionView):
    """``POST .../comunicados/<pk>/destacado/``: ``ComunicadoToggleDestacadoView``."""

    view_class = ComunicadoToggleDestacadoView


class ComunicadoDeleteWebView(_NativeReadView):
    """``/api/web/comedores/comunicados/<pk>/eliminar/``: ``comunicado_confirm_delete.html``.

    Same order as ``ComunicadoDeleteView.dispatch``: the object first (404),
    then the delete permission (403), on GET and on POST.
    """

    http_method_names = ["get", "post"]

    def _view(self, request, pk):
        vista = self.native(ComunicadoDeleteView, request, pk=pk)
        try:
            vista.object = vista.get_object()
        except Http404 as exc:
            raise NotFound() from exc
        if not can_delete_comunicado(request.user, vista.object):
            raise PermissionDenied("No tiene permisos para eliminar este comunicado.")
        return vista

    def get(self, request, pk):
        vista = self._view(request, pk)
        return Response(
            {
                **eliminar_confirmacion(vista.object),
                "messages": pending_messages(request),
            }
        )

    def post(self, request, pk):
        vista = self._view(request, pk)
        # pylint: disable-next=protected-access
        respuesta = vista.post(request._request, pk=pk)
        return Response({"ok": True, "redirect": respuesta["Location"]})


class _ComunicadoFormWebView(_NativeReadView):
    """CM02.02: ``ComunicadoCreateView`` / ``ComunicadoUpdateView`` as JSON.

    GET returns what the native form renders; POST (multipart or urlencoded,
    never JSON) runs the native ``post()``: ``ComunicadoForm``, the attachments
    formset, ``_save_comunicado_with_related`` inside its transaction and the
    native message. A 302 becomes ``{"ok": true, "redirect": ...}``; a form or
    formset rejected by the native view returns 400 with its bound payload.
    """

    http_method_names = ["get", "post"]

    def _view(self, request, pk=None):
        raise NotImplementedError

    def get(self, request, pk=None):
        vista = self._view(request, pk)
        contexto = vista.get_context_data()
        return Response({**formulario(contexto), "messages": pending_messages(request)})

    def post(self, request, pk=None):
        # ``Request.content_type`` keeps the multipart boundary; Django strips it.
        # pylint: disable-next=protected-access
        if request._request.content_type not in (
            "multipart/form-data",
            "application/x-www-form-urlencoded",
        ):
            return Response({"detail": "Formato de solicitud no admitido."}, status=415)
        vista = self._view(request, pk)
        # pylint: disable-next=protected-access
        respuesta = vista.post(request._request)
        if respuesta.status_code == 302:
            return Response({"ok": True, "redirect": respuesta["Location"]})
        return Response(formulario(respuesta.context_data), status=400)


class ComunicadoCreateWebView(_ComunicadoFormWebView):
    """``/api/web/comedores/comunicados/crear/``."""

    def _view(self, request, pk=None):
        # ``ComunicadoCreateView.dispatch``: the check runs on GET and POST.
        require_create_permission(request.user)
        vista = self.native(ComunicadoCreateView, request)
        vista.object = None
        return vista


class ComunicadoUpdateWebView(_ComunicadoFormWebView):
    """``/api/web/comedores/comunicados/<pk>/editar/``."""

    def _view(self, request, pk=None):
        vista = self.native(ComunicadoUpdateView, request, pk=pk)
        try:
            vista.object = vista.get_object()
        except Http404 as exc:
            raise NotFound() from exc
        require_edit_permission(request.user, vista.object)
        return vista


class _DestinatariosWebView(_NativeReadView):
    """CM02.02: the native JSON of the recipients panel, unchanged (same 403 and 404)."""

    view_class = None

    def get(self, request, universo):
        vista = self.native(self.view_class, request)
        # pylint: disable-next=protected-access
        return vista.get(request._request, universo)


class DestinatariosBuscarWebView(_DestinatariosWebView):
    """``GET .../destinatarios/<universo>/buscar/``: ``DestinatariosBuscarView``."""

    view_class = DestinatariosBuscarView


class DestinatariosTodosWebView(_DestinatariosWebView):
    """``GET .../destinatarios/<universo>/todos/``: ``DestinatariosSeleccionarTodosView``."""

    view_class = DestinatariosSeleccionarTodosView
