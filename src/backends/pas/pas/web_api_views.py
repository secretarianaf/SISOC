"""Web API (G1 v1) of the PAS back office: ``/api/web/pas/``.

``/api/web/pas/`` is published by the PAS backend (``url_prefixes`` in
``src/backends/config/backends.json``). In a split deploy the core checks the
session and the web prerequisites and signs each request; the runtime only
serves requests its ``WebGateMiddleware`` verified. In the monolith
``WebGatePermission`` evaluates the same policy locally. After that the native
route rule applies unchanged (``permissions_any_required`` of ``pas/urls.py``),
evaluated with the same ``iam`` function.

Read endpoints run the native views themselves (``PasAreaView``,
``PasFormacionPersonasView`` services, ``PasPersonaListView`` and
``PasPersonaDetailView``) and only project their context to JSON
(``pas.web_api_serializers``). Downloads (DDJJ PDF, tokens XLSX) stay native
GET routes the screen links to.
"""

from django.core.exceptions import PermissionDenied
from django.http import Http404
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import NotFound
from rest_framework.permissions import BasePermission
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.views import APIView

from core.decorators import permissions_any_required
from core.web_gate import WebGatePermission
from iam.services import user_has_permission_code
from pas.services.formacion_service import (
    paginar_personas_formacion,
    preparar_personas_formacion,
)
from pas.views import (
    PasAreaView,
    PasPersonaDetailView,
    PasPersonaListView,
)
from pas import web_api_serializers as proyectar

VIEW = "pas.view_paspersona"


def native_rule(codes):
    """The decorator of the native route, as a DRF permission."""

    regla = permissions_any_required(codes)(lambda request: True)

    class NativeRule(BasePermission):
        def has_permission(self, request, view):
            try:
                return regla(request._request)  # pylint: disable=protected-access
            except PermissionDenied:
                return False

    return NativeRule


class PasWebView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [WebGatePermission, native_rule([VIEW])]
    renderer_classes = [JSONRenderer]
    http_method_names = ["get", "head"]
    native_class = None
    native_kwargs = {}

    def native(self, **kwargs):
        vista = self.native_class(**self.native_kwargs)  # pylint: disable=not-callable
        vista.setup(self.request._request, **kwargs)  # pylint: disable=protected-access
        return vista


class PasAreaWebView(PasWebView):
    """``GET /api/web/pas/areas/<area>/``: the native ``pas/area.html`` context."""

    native_class = PasAreaView
    area_key = None

    def get(self, request):
        vista = self.native()
        vista.area_key = self.area_key
        context = vista.get_context_data()
        data = {
            "area": proyectar.area(context["area"]),
            "workflow": proyectar.workflow(context["pas_areas"]),
            "total_padron": context["total_padron"],
        }
        if self.area_key == "formacion":
            pagina = context["pagina_formacion"]
            seleccionada = context["persona_seleccionada"]
            data.update(
                {
                    "query": context["query"],
                    "estado_formacion": context["estado_formacion"],
                    "persona_solicitada_id": context["persona_solicitada_id"] or None,
                    "personas": [
                        proyectar.persona_formacion(item)
                        for item in context["personas"]
                    ],
                    "has_next": pagina.has_next(),
                    "next_page": (
                        pagina.next_page_number() if pagina.has_next() else None
                    ),
                    "persona_seleccionada": (
                        {
                            "id": seleccionada.pk,
                            "apellidos": seleccionada.apellidos,
                            "nombres": seleccionada.nombres,
                            "dni": seleccionada.dni,
                        }
                        if seleccionada
                        else None
                    ),
                    "resumen": proyectar.resumen_formacion(
                        context["resumen_formacion"]
                    ),
                    "formaciones": [
                        proyectar.formacion(item) for item in context["formaciones_pas"]
                    ],
                }
            )
        return Response(data)


class PasFormacionPersonasWebView(PasWebView):
    """``GET /api/web/pas/formacion/personas/``: the incremental-scroll pages.

    Same parameters and services as ``PasFormacionPersonasView``; the HTML
    fragment becomes items plus the values its links repeat.
    """

    def get(self, request):
        params = request.query_params
        query = (params.get("q") or "").strip()
        estado_formacion = params.get("estado_formacion") or "todos"
        persona_id = params.get("persona")
        excluir_id = int(persona_id) if persona_id and persona_id.isdigit() else None
        pagina = paginar_personas_formacion(
            query=query,
            estado_formacion=estado_formacion,
            pagina=params.get("page", 1),
            excluir_id=excluir_id,
        )
        personas = preparar_personas_formacion(pagina.object_list)
        return Response(
            {
                "personas": [proyectar.persona_formacion(item) for item in personas],
                "has_next": pagina.has_next(),
                "next_page": pagina.next_page_number() if pagina.has_next() else None,
                "query": query,
                "estado_formacion": estado_formacion,
                "persona_seleccionada_id": excluir_id,
            }
        )


class PasPersonaListWebView(PasWebView):
    """``GET /api/web/pas/personas/``: «Buscador PAS» (``PasPersonaListView``)."""

    native_class = PasPersonaListView

    def get(self, request):
        vista = self.native()
        vista.object_list = vista.get_queryset()
        context = vista.get_context_data()
        user = request.user
        django_request = request._request  # pylint: disable=protected-access
        return Response(
            {
                **proyectar.pagina_listado(context, django_request),
                "total_padron": context["total_padron"],
                "query": context["query"],
                "estado_seleccionado": context["estado_seleccionado"],
                "estados": [{"nombre": e.nombre} for e in context["estados_pas"]],
                "capabilities": {
                    "can_import": user_has_permission_code(user, "pas.add_paspersona"),
                    "can_export_tokens": user_has_permission_code(
                        user, "pas.export_ddjj_tokens"
                    ),
                },
                "results": [
                    proyectar.persona_listado(item) for item in context["personas"]
                ],
            }
        )


def panel_payload(request, context):
    """What ``pas/persona_detail.html`` prints."""
    persona = context["persona"]
    return {
        "persona": proyectar.persona_panel(persona) if persona else None,
        "workflow": proyectar.workflow(context["pas_areas"]),
        "query": context["query"],
        "estado_actual": context["estado_actual"],
        "estados_panel": [
            {"id": e.pk, "nombre": e.nombre} for e in context["estados_panel"]
        ],
        "personas_panel": [
            proyectar.persona_mini(item) for item in context["personas_panel"]
        ],
        "ddjj": proyectar.ddjj(
            context["declaraciones_juradas"], context["declaracion_seleccionada"]
        ),
        "formaciones": [
            proyectar.formacion(item) for item in context["formaciones_pas"]
        ],
        "eventos_historial": [
            proyectar.evento(item) for item in context["eventos_historial"]
        ],
        "capabilities": {
            "can_change": user_has_permission_code(
                request.user, "pas.change_paspersona"
            ),
        },
    }


class PasPanelWebView(PasWebView):
    """``GET /api/web/pas/panel/`` and ``/panel/<pk>/``: «Panel de Control».

    Without ``pk`` the first titular by model order; an unknown ``pk`` is 404,
    as in ``PasPersonaDetailView``.
    """

    native_class = PasPersonaDetailView

    def get(self, request, pk=None):
        vista = self.native(**({"pk": pk} if pk is not None else {}))
        try:
            vista.object = vista.get_object()
        except Http404 as exc:
            raise NotFound() from exc
        context = vista.get_context_data(object=vista.object)
        return Response(panel_payload(request, context))
