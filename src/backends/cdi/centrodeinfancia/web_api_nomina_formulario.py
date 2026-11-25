"""Web API (G1 v1) of the CDI nomina form detail (``nomina_formulario_detail.html``) for React.

``/api/web/cdi/`` is published by this backend. In a split deploy the core checks the
session and the web prerequisites and signs each request; the runtime only serves what
its ``WebGateMiddleware`` verified. In the monolith ``WebGatePermission`` evaluates the
same policy locally. After that the native URL guard applies unchanged:
``centrodeinfancia.view_nominacentroinfancia`` (superuser bypass included).

The endpoint runs ``NominaCentroInfanciaFormularioDetailView`` itself (the nomina record
scoped to the actor, 404 outside the scope), so access and object cannot drift from the
HTML page. Each row of the template is rendered here with the same template expression
(``{{ expr|default:"-" }}``, ``yesno``, ``date``), so choice labels, localized dates and
booleans come out identical. The path ``<pk>`` is the nomina id, as in the native URL.
Read-only: GET and HEAD only.
"""

from django.http import Http404
from django.template import Context, Template
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import NotFound
from rest_framework.permissions import BasePermission
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.views import APIView

from centrodeinfancia.views import NominaCentroInfanciaFormularioDetailView
from centrodeinfancia.web_api import pending_messages
from core.decorators import _has_any_permissions
from core.web_gate import WebGatePermission

VER_NOMINA = ["centrodeinfancia.view_nominacentroinfancia"]

# Rows of ``nomina_formulario_detail.html``, in template order: label and the exact
# template expression of its value cell.
FILAS = (
    ("ID", "nomina.id"),
    ("Centro", 'nomina.centro|default:"-"'),
    ("Ciudadano", 'nomina.ciudadano|default:"-"'),
    ("Fecha", 'nomina.fecha|date:"d/m/Y H:i"|default:"-"'),
    ("Estado", 'nomina.get_estado_display|default:"-"'),
    ("DNI", 'nomina.dni|default:"-"'),
    ("Apellido", 'nomina.apellido|default:"-"'),
    ("Nombre", 'nomina.nombre|default:"-"'),
    ("Fecha de nacimiento", 'nomina.fecha_nacimiento|date:"d/m/Y"|default:"-"'),
    ("Edad", 'nomina.edad|default:"-"'),
    ("Sexo", 'nomina.get_sexo_display|default:"-"'),
    ("Nacionalidad", 'nomina.nacionalidad|default:"-"'),
    ("Sala", 'nomina.sala|default:"-"'),
    (
        "Pertenece a pueblo originario",
        'nomina.get_pertenece_pueblo_originario_display|default:"-"',
    ),
    ("Pueblo originario (cuál)", 'nomina.pueblo_originario_cual|default:"-"'),
    (
        "Habla lengua originaria en el hogar",
        'nomina.get_habla_lengua_originaria_hogar_display|default:"-"',
    ),
    ("Talla", 'nomina.talla|default:"-"'),
    ("Peso", 'nomina.peso|default:"-"'),
    (
        "Calendario de vacunación al día",
        'nomina.get_calendario_vacunacion_al_dia_display|default:"-"',
    ),
    ("Tiene discapacidad", 'nomina.get_tiene_discapacidad_display|default:"-"'),
    ("Tipo de discapacidad", 'nomina.get_discapacidad_tipo_display|default:"-"'),
    (
        "Recibe apoyo por discapacidad",
        'nomina.recibe_apoyo_discapacidad|yesno:"Sí,No,-"',
    ),
    ("Posee CUD", 'nomina.posee_cud|yesno:"Sí,No,-"'),
    ("Posee obra social", 'nomina.posee_obra_social|yesno:"Sí,No,-"'),
    ("Calle domicilio", 'nomina.calle_domicilio|default:"-"'),
    ("Altura domicilio", 'nomina.altura_domicilio|default:"-"'),
    ("Piso domicilio", 'nomina.piso_domicilio|default:"-"'),
    ("Departamento domicilio", 'nomina.departamento_domicilio|default:"-"'),
    ("Provincia domicilio", 'nomina.provincia_domicilio|default:"-"'),
    ("Departamento (jurisdicción)", 'nomina.departamento|default:"-"'),
    ("Decil de CDI", 'nomina.departamento.decil_ipi|default:"-"'),
    ("Municipio domicilio", 'nomina.municipio_domicilio|default:"-"'),
    ("Localidad domicilio", 'nomina.localidad_domicilio|default:"-"'),
    (
        "Responsable legal 1 - Apellido",
        'nomina.responsable_legal_1_apellido|default:"-"',
    ),
    ("Responsable legal 1 - Nombre", 'nomina.responsable_legal_1_nombre|default:"-"'),
    ("Responsable legal 1 - DNI", 'nomina.responsable_legal_1_dni|default:"-"'),
    (
        "Responsable legal 1 - Teléfono",
        'nomina.responsable_legal_1_telefono|default:"-"',
    ),
    (
        "Responsable legal 1 - Percibe AUH",
        'nomina.get_responsable_legal_1_percibe_auh_display|default:"-"',
    ),
    (
        "Responsable legal 1 - Percibe Alimenta",
        'nomina.get_responsable_legal_1_percibe_alimenta_display|default:"-"',
    ),
    (
        "Responsable legal 2 - Apellido",
        'nomina.responsable_legal_2_apellido|default:"-"',
    ),
    ("Responsable legal 2 - Nombre", 'nomina.responsable_legal_2_nombre|default:"-"'),
    ("Responsable legal 2 - DNI", 'nomina.responsable_legal_2_dni|default:"-"'),
    (
        "Responsable legal 2 - Teléfono",
        'nomina.responsable_legal_2_telefono|default:"-"',
    ),
    (
        "Responsable legal 2 - Percibe AUH",
        'nomina.get_responsable_legal_2_percibe_auh_display|default:"-"',
    ),
    (
        "Responsable legal 2 - Percibe Alimenta",
        'nomina.get_responsable_legal_2_percibe_alimenta_display|default:"-"',
    ),
    ("Adulto responsable - Apellido", 'nomina.adulto_responsable_apellido|default:"-"'),
    ("Adulto responsable - Nombre", 'nomina.adulto_responsable_nombre|default:"-"'),
    ("Adulto responsable - DNI", 'nomina.adulto_responsable_dni|default:"-"'),
    ("Adulto responsable - Teléfono", 'nomina.adulto_responsable_telefono|default:"-"'),
    (
        "Adulto responsable - Parentesco",
        'nomina.adulto_responsable_parentesco|default:"-"',
    ),
    ("Observaciones", 'nomina.observaciones|default:"-"'),
)

_PLANTILLAS = {}


def _render(contexto, expresion):
    if expresion not in _PLANTILLAS:
        _PLANTILLAS[expresion] = Template("{{ " + expresion + " }}")
    return _PLANTILLAS[expresion].render(contexto)


class PuedeVerNomina(BasePermission):
    """Same rule as the native ``permissions_any_required`` on the form detail URL."""

    def has_permission(self, request, view):
        return _has_any_permissions(request.user, VER_NOMINA)


class NominaFormularioWebView(APIView):
    """``GET /api/web/cdi/nomina/<pk>/formulario/``."""

    authentication_classes = [SessionAuthentication]
    permission_classes = [WebGatePermission, PuedeVerNomina]
    renderer_classes = [JSONRenderer]
    http_method_names = ["get", "head"]

    def get(self, request, pk):
        django_request = request._request  # pylint: disable=protected-access
        vista = NominaCentroInfanciaFormularioDetailView()
        vista.setup(django_request, pk=pk)
        try:
            vista.object = vista.get_object()
        except Http404 as exc:
            raise NotFound() from exc
        contexto = Context({"nomina": vista.object}, autoescape=False)
        return Response(
            {
                "rows": [
                    {"label": etiqueta, "value": _render(contexto, expresion)}
                    for etiqueta, expresion in FILAS
                ],
                "messages": pending_messages(django_request),
            }
        )
