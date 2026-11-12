"""Web API (G1 v1) of the PAS reports (PAS04): ``/api/web/pas/informes/``.

Same access as the native routes of ``pas/urls.py``: G1 first
(``WebGatePermission``), then ``permissions_all_required`` with the route's
codes, evaluated with the same ``iam`` function. Reads run the native views
(``PasInformeListView``, ``PasInformeDetailView``) and project their context;
the CSV download stays the native GET ``pas/informes/<pk>/descargar``, which
the screen only links when the user holds its three codes.

The request of a new report (PAS04.02) shares the native form and services:
``opciones/`` lists the form choices, ``previsualizar/`` is the native preview
and ``generar/`` creates the report and answers its CSV in the same response
(the native POST does the same, with ``add_pasinforme`` only).
"""

from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.template import Context, Template
from django.utils.cache import patch_vary_headers
from django.urls import reverse
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import NotFound
from rest_framework.permissions import BasePermission
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.views import APIView

from core.decorators import permissions_all_required
from core.web_gate import WebGatePermission
from iam.services import user_has_permission_code
from pas import web_api_serializers as proyectar
from pas.forms import PasInformeGenerarForm
from pas.services.informe_service import (
    CSV_COLUMNS,
    csv_response_for_informe,
    errors_payload,
    generar_informe_pas,
    preview_payload,
)
from pas.views import (
    PasInformeDetailView,
    PasInformeListView,
    _breadcrumb_informes,
)

VIEW = "pas.view_paspersona"
VIEW_INFORME = "pas.view_pasinforme"
ADD_INFORME = "pas.add_pasinforme"
EXPORT_CSV = "auth.role_exportar_a_csv"
READ_CODES = [VIEW, VIEW_INFORME]
GENERATE_CODES = [VIEW, ADD_INFORME]
DOWNLOAD_CODES = [VIEW, VIEW_INFORME, EXPORT_CSV]

# ``informe_detail.html``: the chip value of each saved filter.
_FILTER_VALUE = Template(
    "{% autoescape off %}{% if value.label %}{{ value.label }}"
    "{% else %}{{ value }}{% endif %}{% endautoescape %}"
)


def native_all_rule(codes):
    """The ``permissions_all_required`` decorator of the native route, as a DRF permission."""

    regla = permissions_all_required(codes)(lambda request: True)

    class NativeAllRule(BasePermission):
        def has_permission(self, request, view):
            try:
                return regla(request._request)  # pylint: disable=protected-access
            except PermissionDenied:
                return False

    return NativeAllRule


def has_all(user, codes):
    return all(user_has_permission_code(user, code) for code in codes)


def usuario(user):
    """``usuario.get_full_name|default:usuario.username``; ``""`` lets the screen print «-»."""
    if user is None:
        return ""
    return user.get_full_name() or user.username


def download_url(informe, can_download):
    if not can_download:
        return None
    return reverse("pas_informe_descargar", kwargs={"pk": informe.pk})


def informe_resumen(informe, can_download):
    return {
        "id": informe.pk,
        "numero": informe.numero,
        "creado": proyectar.fecha_hora(informe.creado),
        "usuario": usuario(informe.usuario),
        "total_personas": informe.total_personas,
        "total_cambios": informe.total_cambios,
        "detail_path": reverse("pas_informe_detalle", kwargs={"pk": informe.pk}),
        "download_url": download_url(informe, can_download),
    }


def filtros(informe):
    """Saved filters in their stored order, with the key as stored (not translated)."""
    guardados = informe.filtros if isinstance(informe.filtros, dict) else {}
    return [
        {"clave": str(clave), "valor": _FILTER_VALUE.render(Context({"value": valor}))}
        for clave, valor in guardados.items()
    ]


def celda(row, key):
    """``{{ row.<key> }}``: the stored value as the template prints it."""
    if not isinstance(row, dict) or key not in row:
        return ""
    return str(row[key])


def breadcrumb(items):
    """``components/breadcrumb.html``: the active item does not link."""
    return [
        {"text": str(item["text"]), "url": None if item.get("active") else item["url"]}
        for item in items
    ]


class PasInformeWebView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [WebGatePermission, native_all_rule(READ_CODES)]
    renderer_classes = [JSONRenderer]
    http_method_names = ["get", "head"]
    native_class = None

    def native(self, **kwargs):
        vista = self.native_class()  # pylint: disable=not-callable
        vista.setup(self.request._request, **kwargs)  # pylint: disable=protected-access
        return vista


class PasInformeListWebView(PasInformeWebView):
    """``GET /api/web/pas/informes/?q=&page=``: «Informes PAS» (``PasInformeListView``)."""

    native_class = PasInformeListView

    def get(self, request):
        vista = self.native()
        vista.object_list = vista.get_queryset()
        context = vista.get_context_data()
        user = request.user
        can_download = has_all(user, DOWNLOAD_CODES)
        django_request = request._request  # pylint: disable=protected-access
        return Response(
            {
                **proyectar.pagina_listado(context, django_request),
                "breadcrumb": breadcrumb(context["breadcrumb_items"]),
                "query": context["query"],
                "can_generate": has_all(user, GENERATE_CODES),
                "results": [
                    informe_resumen(item, can_download) for item in context["informes"]
                ],
            }
        )


class PasInformeDetailWebView(PasInformeWebView):
    """``GET /api/web/pas/informes/<pk>/``: one report as ``informe_detail.html`` prints it.

    The rows are the saved snapshot (``resultado``), never recalculated and not
    paginated, as in the template.
    """

    native_class = PasInformeDetailView

    def get(self, request, pk):
        vista = self.native(pk=pk)
        try:
            vista.object = vista.get_object()
        except Http404 as exc:
            raise NotFound() from exc
        context = vista.get_context_data(object=vista.object)
        informe = context["informe"]
        resultado = informe.resultado if isinstance(informe.resultado, list) else []
        return Response(
            {
                "id": informe.pk,
                "numero": informe.numero,
                "creado": proyectar.fecha_hora(informe.creado),
                "usuario": usuario(informe.usuario),
                "total_personas": informe.total_personas,
                "total_cambios": informe.total_cambios,
                "breadcrumb": breadcrumb(context["breadcrumb_items"]),
                "filtros": filtros(informe),
                "columns": [{"key": key, "label": label} for key, label in CSV_COLUMNS],
                "rows": [
                    [celda(row, key) for key, _ in CSV_COLUMNS] for row in resultado
                ],
                "download_url": download_url(
                    informe, has_all(request.user, DOWNLOAD_CODES)
                ),
            }
        )


class PasInformeGenerarWebView(APIView):
    """Base of the request routes: same access as ``pas/informes/generar``."""

    authentication_classes = [SessionAuthentication]
    permission_classes = [WebGatePermission, native_all_rule(GENERATE_CODES)]
    renderer_classes = [JSONRenderer]


class PasInformeOpcionesWebView(PasInformeGenerarWebView):
    """``GET /api/web/pas/informes/opciones/?provincia=<id>``: the choices of the form.

    Read from the form's own querysets: the order is the form's, and the
    municipios are the ones the form accepts for that province (none without one).
    """

    http_method_names = ["get", "head"]

    def get(self, request):
        provincia = request.query_params.get("provincia", "")
        form = PasInformeGenerarForm({"provincia": provincia})
        campos = form.fields
        return Response(
            {
                "breadcrumb": breadcrumb(_breadcrumb_informes("Generar")),
                "estados": [
                    {"id": item.pk, "nombre": item.nombre}
                    for item in campos["estado_actual"].queryset
                ],
                "avisos": [
                    {"id": item.pk, "texto": str(item)}
                    for item in campos["aviso_actual"].queryset
                ],
                "provincias": [
                    {"id": item.pk, "nombre": item.nombre}
                    for item in campos["provincia"].queryset
                ],
                "municipios": [
                    {"id": item.pk, "nombre": item.nombre}
                    for item in campos["municipio"].queryset
                ],
            }
        )


class PasInformePrevisualizarWebView(PasInformeGenerarWebView):
    """``POST /api/web/pas/informes/previsualizar/``: ``PasInformePreviewView`` as is."""

    http_method_names = ["post"]

    def post(self, request):
        form = PasInformeGenerarForm(request.POST)
        if not form.is_valid():
            return Response(errors_payload(form), status=400)
        return Response(preview_payload(form))


class PasInformeGenerarCsvWebView(PasInformeGenerarWebView):
    """``POST /api/web/pas/informes/generar/``: creates one report and answers its CSV.

    The CSV comes back in the same response, as in the native view: that route
    only needs ``add_pasinforme``, while the later download also needs the export
    code, so splitting them would change who gets the file. A form error is the
    native re-render as JSON (400) and creates nothing.
    """

    http_method_names = ["post"]

    def post(self, request):
        form = PasInformeGenerarForm(request.POST)
        if not form.is_valid():
            return Response(errors_payload(form), status=400)
        informe = generar_informe_pas(form, usuario=request.user)
        response = csv_response_for_informe(informe)
        response["X-PAS-Informe-Id"] = str(informe.pk)
        response["Cache-Control"] = "private, no-store"
        patch_vary_headers(response, ("Cookie",))
        return response
