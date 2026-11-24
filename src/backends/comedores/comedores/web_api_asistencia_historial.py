"""Web API (G1 v1) of the monthly attendance history of the nómina (CO01).

``GET /api/web/comedores/comedores/<pk>/admision/<admision_pk>/nomina/asistencia/``.

In a split deploy the core checks the session and the web prerequisites and
signs each request; the runtime only serves requests its ``WebGateMiddleware``
verified. In the monolith ``WebGatePermission`` evaluates the same policy
locally. After that the native route guard applies unchanged (superuser bypass
included): ``nomina_asistencia_historial`` is
``permissions_any_required(["comedores.view_nomina"])``.

The endpoint runs the native ``NominaAsistenciaHistorialView`` itself
(``setup()`` and ``get_context_data()``: comedor and admission scope, month
list with its latest generated document, selected period and attendees), and
renders every text with the expression of ``nomina_asistencia_historial.html``
(localization, ``default``, ``m/Y`` and ``d/m/Y H:i`` formats). It only reads:
the attendance is written by the PWA producer, and the generated PDF stays a
native file link (``archivo.url``), never moved to the client.
"""

from django.http import Http404
from django.template import Context, Template
from django.urls import reverse
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import NotFound
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.views import APIView

from core.web_gate import WebGatePermission
from comedores.views.nomina import NominaAsistenciaHistorialView
from comedores.web_api_comedores import pending_messages
from comedores.web_api_nomina import VerNomina

_TEMPLATES = {}

# Expressions of ``nomina_asistencia_historial.html``.
_PERIODO = {
    "label": '{{ item.periodo_referencia|date:"m/Y" }}',
    "iso": "{{ item.periodo_referencia|date:'Y-m-d' }}",
    "total": "{{ item.total_asistentes }}",
    "documento": "{{ item.documento_nomina.archivo.url }}",
}
_ASISTENTE = {
    "apellido": '{{ r.nomina.ciudadano.apellido|default:"-" }}',
    "nombre": '{{ r.nomina.ciudadano.nombre|default:"-" }}',
    "documento": '{{ r.nomina.ciudadano.documento|default:"-" }}',
    "genero": '{{ r.nomina.ciudadano.sexo.sexo|default:"-" }}',
    "tomada_el": '{{ r.fecha_toma_asistencia|date:"d/m/Y H:i" }}',
    "tomada_por": '{{ r.tomado_por.username|default:"-" }}',
}


def _render(expression, context):
    if expression not in _TEMPLATES:
        _TEMPLATES[expression] = Template(expression)
    return _TEMPLATES[expression].render(context).strip()


def _periodo(item):
    context = Context({"item": item}, autoescape=False)
    documento = item["documento_nomina"]
    return {
        "label": _render(_PERIODO["label"], context),
        "iso": _render(_PERIODO["iso"], context),
        "total": _render(_PERIODO["total"], context),
        # A document row without its file has no link (the native page fails there).
        "documento_url": (
            _render(_PERIODO["documento"], context)
            if documento is not None and documento.archivo
            else None
        ),
    }


def _asistente(registro):
    context = Context({"r": registro}, autoescape=False)
    cells = {key: _render(expr, context) for key, expr in _ASISTENTE.items()}
    ciudadano_id = registro.nomina.ciudadano_id
    return {
        "id": registro.pk,
        **cells,
        "ciudadano_url": (
            reverse("ciudadanos_ver", args=[ciudadano_id]) if ciudadano_id else None
        ),
    }


class NominaAsistenciaHistorialWebView(APIView):
    """Read-only projection of ``NominaAsistenciaHistorialView``."""

    authentication_classes = [SessionAuthentication]
    permission_classes = [WebGatePermission, VerNomina]
    renderer_classes = [JSONRenderer]
    http_method_names = ["get", "head"]

    def get(self, request, pk, admision_pk):
        django_request = request._request  # pylint: disable=protected-access
        vista = NominaAsistenciaHistorialView()
        vista.setup(django_request, pk=pk, admision_pk=admision_pk)
        try:
            context = vista.get_context_data()
        except Http404 as exc:
            raise NotFound() from exc
        comedor = context["object"]
        seleccionado = context["asistencia_periodo_seleccionado"]
        contexto = Context(context, autoescape=False)
        return Response(
            {
                "comedor": {"id": comedor.pk, "nombre": str(comedor.nombre)},
                "periodo": (
                    {
                        "label": _render(
                            '{{ asistencia_periodo_seleccionado|date:"m/Y" }}',
                            contexto,
                        ),
                        "total": _render("{{ asistencia_total }}", contexto),
                    }
                    if seleccionado
                    else None
                ),
                "asistentes": [_asistente(r) for r in context["asistencia_asistentes"]],
                "periodos": [_periodo(item) for item in context["asistencia_periodos"]],
                "urls": {
                    "comedores": reverse("comedores"),
                    "comedor": reverse("comedor_detalle", args=[comedor.pk]),
                    "nomina": reverse("nomina_ver", args=[comedor.pk, admision_pk]),
                    "historial": reverse(
                        "nomina_asistencia_historial", args=[comedor.pk, admision_pk]
                    ),
                },
                "messages": pending_messages(django_request),
            }
        )
