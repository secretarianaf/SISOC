"""Web API (G1 v1) of the comunicados pages served by React (CM03.01).

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
from rest_framework.exceptions import NotFound
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.views import APIView

from comunicados.views import ComunicadoDetailView, ComunicadoListView
from comunicados.web_api_serializers import (
    detalle,
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
