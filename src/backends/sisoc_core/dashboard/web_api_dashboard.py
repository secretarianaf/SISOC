"""Dashboards and embedded boards for React (D01, G1 v1).

``GET /api/web/dashboard/centro-de-familia/`` runs ``DashboardView`` (login only, as the native URL) and
projects the context of ``dashboard.html``: the Comedores indicators arrive as the template prints them
(``default_if_none:"Sin información"``) and the page keeps its native freshness rule (the portal keeps its
last values when the remote source fails; a zero never stands for missing data). ``GET
/api/web/dashboard/<slug>/`` runs ``TableroEmbedView`` (403 when ``usuario_puede_ver`` denies, 404 for an
inactive or unknown board; a board with its own screen answers the native redirect). Read only.
"""

from django.contrib import messages
from django.http import Http404, HttpResponseRedirect
from django.utils.cache import patch_cache_control, patch_vary_headers
from django.utils.formats import localize
from django.views import View
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import NotFound
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.views import APIView

from core.templatetags.custom_filters import has_perm_code
from core.web_gate import WebGatePermission
from dashboard.views import DashboardView, TableroEmbedView

SIN_INFORMACION = "Sin información"
LEVELS = {
    messages.DEBUG: "info",
    messages.INFO: "info",
    messages.SUCCESS: "success",
    messages.WARNING: "warning",
    messages.ERROR: "error",
}
METRICAS = (
    "cantidad_comedores_activos",
    "cantidad_relevamientos_activos",
    "presupuesto_desayuno",
    "presupuesto_merienda",
    "presupuesto_comida",
)


def pending_messages(request):
    """Consume the queued flash messages as the native page does."""
    return [
        {"message": str(message), "level": LEVELS.get(message.level, "info")}
        for message in messages.get_messages(request)
    ]


class DashboardNativeWebView(APIView):
    """Guards (session, G1) and then the native view, run on the same request."""

    authentication_classes = [SessionAuthentication]
    permission_classes = [WebGatePermission]
    renderer_classes = [JSONRenderer]
    native_view = View
    http_method_names = ["get", "head", "options"]

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        patch_cache_control(response, private=True, no_store=True)
        patch_vary_headers(response, ("Cookie",))
        return response

    def run_native(self, request, **kwargs):
        # pylint: disable-next=protected-access
        django_request = request._request
        view = self.native_view()
        view.setup(django_request, **kwargs)
        try:
            return view.dispatch(django_request, **kwargs)
        except Http404 as exc:
            raise NotFound() from exc


def _valor(value):
    """``{{ value|default_if_none:"Sin información" }}``."""
    return SIN_INFORMACION if value is None else localize(value)


def proyectar_dashboard(context, request):
    """Context of ``dashboard.html`` as the template prints it."""
    can_view = has_perm_code(request.user, "dashboard.view_dashboard")
    return {
        "can_view": can_view,
        "metricas_desactualizadas": bool(context["metricas_comedores_desactualizadas"]),
        "metricas_disponibles": bool(context["metricas_comedores_disponibles"]),
        # The native page only prints the indicators for ``view_dashboard``: nothing else leaves.
        "metricas": (
            {clave: _valor(context[clave]) for clave in METRICAS} if can_view else None
        ),
        "messages": pending_messages(request),
    }


def proyectar_tablero(tablero, request):
    """Context of ``dashboard_tablero.html``."""
    return {
        "titulo": tablero.titulo,
        "nombre": tablero.nombre,
        "url": tablero.url or "",
        "embed_url": tablero.get_embed_url() if tablero.url else "",
        "looker_compartible": bool(
            tablero.url and tablero.usa_url_compartible_looker_studio()
        ),
        "mensaje_construccion": (
            "" if tablero.url else tablero.get_mensaje_construccion()
        ),
        "messages": pending_messages(request),
    }


class DashboardWebView(DashboardNativeWebView):
    native_view = DashboardView

    def get(self, request):
        response = self.run_native(request)
        # pylint: disable-next=protected-access
        return Response(proyectar_dashboard(response.context_data, request._request))


class TableroWebView(DashboardNativeWebView):
    native_view = TableroEmbedView

    def get(self, request, slug):
        response = self.run_native(request, slug=slug)
        if isinstance(response, HttpResponseRedirect):
            return Response({"redirect": response["Location"]})
        django_request = request._request  # pylint: disable=protected-access
        return Response(
            proyectar_tablero(response.context_data["tablero"], django_request)
        )
