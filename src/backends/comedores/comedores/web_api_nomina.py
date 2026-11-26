"""Web API (G1 v1) of the comedor nómina read (CO01): ``/api/web/comedores/comedores/``.

``/api/web/comedores/`` is published by the comedores backend. In a split
deploy the core checks the session and the web prerequisites and signs each
request; the runtime only serves requests its ``WebGateMiddleware`` verified.
In the monolith ``WebGatePermission`` evaluates the same policy locally. After
that the native route guard applies unchanged (superuser bypass included):

- ``nomina_ver`` / ``nomina_directa_ver``:
  ``permissions_any_required(["comedores.view_nomina"])``.

The endpoints run the native ``NominaDetailView`` and
``NominaDirectaDetailView`` themselves (``setup()`` and
``get_context_data()``: scoped comedor, admission of that comedor, tab, DNI
filter, page of 100, metrics and age ranges), so scope and numbers cannot drift
from ``nomina_detail.html``. Every text is rendered with the expression of that
template (localization, ``default``, date formats). Reading never writes. The
add, edit, state, derive, delete and import actions stay native.
"""

from django.http import Http404
from django.template import Context, Template
from django.urls import reverse
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import NotFound
from rest_framework.permissions import BasePermission
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.views import APIView

from core.decorators import _has_any_permissions
from core.web_gate import WebGatePermission
from comedores.views.nomina import NominaDetailView, NominaDirectaDetailView
from comedores.web_api_comedores import pending_messages

VER_NOMINA = ["comedores.view_nomina"]

_TEMPLATES = {}

# Expressions of ``nomina_detail.html``; the whole text of each metric ``<span>``.
_STATS = {
    "asistentes": "{{ cantidad_nomina }}",
    "espera": "{{ espera }}",
    "baja": "{{ nomina_rangos.baja|default:0 }}",
    "hombres": "{{ nominaM }}",
    "mujeres": "{{ nominaF }}",
    "no_binarios": "{{ nominaX|default:0 }}",
    "ninos": "{{ nomina_rangos.ninos|default:0 }}",
    "adolescentes": "{{ nomina_rangos.adolescentes|default:0 }}",
    "adultos": "{{ nomina_rangos.adultos|default:0 }}",
    "adultos_mayores": "{{ nomina_rangos.adultos_mayores|default:0 }}",
    "adulto_mayor_avanzado": "{{ nomina_rangos.adulto_mayor_avanzado|default:0 }}",
}
# The template reads these three names, but the views never set them.
_HEADER = {
    "inicio": '{{ ejecucion_inicio|date:"d/m/Y"|default:"-" }}',
    "fin": '{{ ejecucion_fin|date:"d/m/Y"|default:"-" }}',
    "plazo": '{{ plazo_ejecucion|default:"-" }}',
}
_CELLS = {
    "fecha": '{{ e.fecha|date:"d/m/Y" }}',
    "nombre": "{{ e.ciudadano.nombre }}",
    "apellido": "{{ e.ciudadano.apellido }}",
    "documento": '{{ e.ciudadano.documento|default:"-" }}',
    "sexo": '{{ e.ciudadano.sexo.sexo|default:"-" }}',
    "estado_label": "{{ e.get_estado_display }}",
    "derivar_nombre": "{{ e.ciudadano.nombre }} {{ e.ciudadano.apellido }}",
}


class VerNomina(BasePermission):
    """Same rule as the native ``permissions_any_required`` of the nómina URLs."""

    def has_permission(self, request, view):
        return _has_any_permissions(request.user, VER_NOMINA)


def render(expression, context):
    if expression not in _TEMPLATES:
        _TEMPLATES[expression] = Template(expression)
    return _TEMPLATES[expression].render(context).strip()


def _row(registro, comedor_id, admision_pk):
    context = Context({"e": registro}, autoescape=False)
    cells = {key: render(expr, context) for key, expr in _CELLS.items()}
    if admision_pk:
        borrar = reverse("nomina_borrar", args=[comedor_id, admision_pk, registro.pk])
    else:
        borrar = reverse("nomina_directa_borrar", args=[comedor_id, registro.pk])
    return {
        "id": registro.pk,
        "estado": registro.estado,
        "ciudadano_id": registro.ciudadano_id,
        "comunidad_indigena": bool(registro.pwa_comunidad_indigena),
        "situacion_calle": bool(registro.pwa_situacion_calle),
        "celiaquia": bool(registro.pwa_persona_con_celiaquia),
        **cells,
        "urls": {
            "ciudadano": reverse("ciudadanos_ver", args=[registro.ciudadano_id]),
            "cambiar_estado": reverse("nomina_cambiar_estado", args=[registro.pk]),
            "derivar": reverse("nomina_derivar", args=[registro.pk]),
            "borrar": borrar,
        },
    }


class _NominaWebView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [WebGatePermission, VerNomina]
    renderer_classes = [JSONRenderer]
    http_method_names = ["get", "head"]

    @staticmethod
    def project(request, native_view, **kwargs):
        django_request = request._request  # pylint: disable=protected-access
        vista = native_view()
        vista.setup(django_request, **kwargs)
        try:
            context = vista.get_context_data()
        except Http404 as exc:
            raise NotFound() from exc
        comedor, pagina = context["object"], context["nomina"]
        admision_pk = context["admision_pk"]
        contexto = Context(context, autoescape=False)
        if admision_pk:
            lista = reverse("nomina_ver", args=[comedor.pk, admision_pk])
            historial = reverse(
                "nomina_asistencia_historial", args=[comedor.pk, admision_pk]
            )
            crear = reverse("nomina_crear", args=[comedor.pk, admision_pk])
        else:
            lista = reverse("nomina_directa_ver", args=[comedor.pk])
            historial = None
            crear = reverse("nomina_directa_crear", args=[comedor.pk])
        return Response(
            {
                "comedor": {
                    "id": comedor.pk,
                    "nombre": str(comedor.nombre),
                    "provincia": (
                        str(comedor.provincia.nombre) if comedor.provincia else None
                    ),
                    "municipio": (
                        str(comedor.municipio.nombre) if comedor.municipio else None
                    ),
                },
                "header": {k: render(e, contexto) for k, e in _HEADER.items()},
                "stats": {k: render(e, contexto) for k, e in _STATS.items()},
                "tabs": (
                    [dict(o) for o in context["nomina_tab_options"]]
                    if context["mostrar_tabs_nomina"]
                    else None
                ),
                "tab": context["nomina_tab"],
                "dni": context["dni_query"],
                "can_view_ciudadano": bool(
                    request.user.has_perm("ciudadanos.view_ciudadano")
                ),
                "rows": [_row(e, comedor.pk, admision_pk) for e in pagina],
                "page": {
                    "has_other_pages": pagina.has_other_pages(),
                    "number": pagina.number,
                    "num_pages": pagina.paginator.num_pages,
                    "count": pagina.paginator.count,
                    "start": pagina.start_index(),
                    "end": pagina.end_index(),
                    "previous": (
                        pagina.previous_page_number() if pagina.has_previous() else None
                    ),
                    "next": pagina.next_page_number() if pagina.has_next() else None,
                },
                "estados": [[value, str(label)] for value, label in context["estados"]],
                "comedores_para_derivar": [
                    {"id": c["id"], "nombre": str(c["nombre"])}
                    for c in context["comedores_para_derivar"]
                ],
                "urls": {
                    "comedores": reverse("comedores"),
                    "comedor": reverse("comedor_detalle", args=[comedor.pk]),
                    "lista": lista,
                    "historial": historial,
                    "crear": crear,
                },
                "messages": pending_messages(django_request),
            }
        )


class NominaAdmisionWebView(_NominaWebView):
    """``GET /api/web/comedores/comedores/<pk>/admision/<admision_pk>/nomina/``."""

    def get(self, request, pk, admision_pk):
        return self.project(request, NominaDetailView, pk=pk, admision_pk=admision_pk)


class NominaDirectaWebView(_NominaWebView):
    """``GET /api/web/comedores/comedores/<pk>/nomina/``: direct nómina, no admission."""

    def get(self, request, pk):
        return self.project(request, NominaDirectaDetailView, pk=pk)
