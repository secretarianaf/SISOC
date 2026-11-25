"""Web API (G1 v1) of the CDI beneficiary detail (CDI04.01) for the React page.

``/api/web/cdi/`` is published by this backend. In a split deploy the core
checks the session and the web prerequisites and signs each request; the
runtime only serves what its ``WebGateMiddleware`` verified. In the monolith
``WebGatePermission`` evaluates the same policy locally. After that the native
URL guard applies unchanged: ``centrodeinfancia.view_centrodeinfancia`` through
the same predicate as ``permissions_any_required`` (superuser bypass included).

The endpoint runs ``NominaCentroInfanciaDestinatariosDetailView`` itself (the
scoped centre and the scoped nómina record, both 404 outside the actor's
scope), so access and objects cannot drift from the HTML page. Each field of
``destinatario_detail.html`` is rendered here with the same template
expression as the native page (``{{ expr|default:"—" }}``), so choice labels,
localized dates and ``yesno`` come out identical; the React page only draws
the sections. Read-only: GET and HEAD only; the edit link keeps the native
permission check.
"""

from django.http import Http404
from django.template import Context, Template
from django.template.base import Variable, VariableDoesNotExist
from django.urls import reverse
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import NotFound
from rest_framework.permissions import BasePermission
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.views import APIView

from centrodeinfancia.views import NominaCentroInfanciaDestinatariosDetailView
from centrodeinfancia.web_api import pending_messages
from core.decorators import _has_any_permissions
from core.web_gate import WebGatePermission

VER_CENTRO = ["centrodeinfancia.view_centrodeinfancia"]
VACIO = "—"

# Fields of each section, in the order of ``destinatario_detail.html``. A CUIT
# entry carries a third item: the flag that replaces it with "No posee CUIL".
_CAMPOS_REGISTRO = (
    ("Estado", "nomina.get_estado_display"),
    ("Tipo de registro", "nomina.get_tipo_registro_display"),
    ("Fecha de registro", "nomina.fecha_registro"),
    ("Trabajador/a que registra", "nomina.trabajador_registra"),
    ("CDI", "centro.nombre"),
    ("Código CDI", "centro.codigo_cdi"),
)

_CAMPOS_NINO = (
    ("Apellido", "nomina.apellido"),
    ("Nombre", "nomina.nombre"),
    ("Fecha de nacimiento", "nomina.fecha_nacimiento"),
    ("Edad", "nomina.edad_display"),
    ("Sexo registral", "nomina.get_sexo_display"),
    ("Tipo de documentación", "nomina.get_tipo_documentacion_display"),
    ("DNI", "nomina.dni"),
    ("CUIT", "nomina.cuit_nino", "nomina.sin_cuil_nino"),
    ("País de nacimiento", "nomina.pais_nacimiento"),
    ("Nacionalidad", "nomina.nacionalidad"),
    ("Sala", "nomina.sala"),
)

_CAMPOS_RESPONSABLE1 = (
    ("Relación", "nomina.get_responsable_legal_1_relacion_display"),
    ("Apellido", "nomina.responsable_legal_1_apellido"),
    ("Nombre", "nomina.responsable_legal_1_nombre"),
    ("Fecha de nacimiento", "nomina.responsable_legal_1_fecha_nacimiento"),
    ("Tipo doc.", "nomina.get_responsable_legal_1_tipo_documentacion_display"),
    ("DNI", "nomina.responsable_legal_1_dni"),
    ("CUIT", "nomina.responsable_legal_1_cuit", "nomina.responsable_legal_1_sin_cuil"),
    ("Teléfono", "nomina.responsable_legal_1_telefono"),
    ("País de nacimiento", "nomina.responsable_legal_1_pais_nacimiento"),
    ("Nacionalidad", "nomina.responsable_legal_1_nacionalidad"),
    ("Sexo registral", "nomina.get_responsable_legal_1_sexo_registral_display"),
    ("Nivel educativo", "nomina.get_responsable_legal_1_nivel_educativo_display"),
    ("Consentimiento", "nomina.get_responsable_legal_1_consentimiento_display"),
)

_CAMPOS_RESPONSABLE2 = (
    ("Relación", "nomina.get_responsable_legal_2_relacion_display"),
    ("Apellido", "nomina.responsable_legal_2_apellido"),
    ("Nombre", "nomina.responsable_legal_2_nombre"),
    ("Fecha de nacimiento", "nomina.responsable_legal_2_fecha_nacimiento"),
    ("Tipo doc.", "nomina.get_responsable_legal_2_tipo_documentacion_display"),
    ("DNI", "nomina.responsable_legal_2_dni"),
    ("CUIT", "nomina.responsable_legal_2_cuit"),
    ("Teléfono", "nomina.responsable_legal_2_telefono"),
    ("País de nacimiento", "nomina.responsable_legal_2_pais_nacimiento"),
    ("Nacionalidad", "nomina.responsable_legal_2_nacionalidad"),
    ("Sexo registral", "nomina.get_responsable_legal_2_sexo_registral_display"),
    ("Nivel educativo", "nomina.get_responsable_legal_2_nivel_educativo_display"),
    ("Consentimiento", "nomina.get_responsable_legal_2_consentimiento_display"),
)

_CAMPOS_DOMICILIO = (
    ("Calle", "nomina.calle_domicilio"),
    ("Altura", "nomina.altura_domicilio"),
    ("Piso", "nomina.piso_domicilio"),
    ("Dpto.", "nomina.departamento_domicilio"),
    ("Tipo de barrio", "nomina.get_tipo_barrio_display"),
    ("Jurisdicción", "nomina.provincia_domicilio"),
    ("Departamento (jurisdicción)", "nomina.departamento"),
    ("Decil de CDI", "nomina.departamento.decil_ipi"),
    ("Municipio", "nomina.municipio_domicilio"),
    ("Localidad", "nomina.localidad_domicilio"),
    ("Convivientes", "nomina.convivientes"),
)

_CAMPOS_CULTURA = (
    ("¿Necesita intérprete?", "nomina.get_necesito_interprete_display"),
    ("Pueblo originario", "nomina.pueblo_originario_cual"),
)

_CAMPOS_DISCAPACIDAD = (
    ("¿Tiene discapacidad?", "nomina.get_tiene_discapacidad_display"),
    ("¿Recibe apoyo al desarrollo?", "nomina.apoyo_desarrollo_unificado_display"),
    ("¿Posee CUD?", 'nomina.posee_cud|yesno:"Sí,No,—"'),
    ("N° CUD", "nomina.numero_cud"),
)

_CAMPOS_SALUD = (
    ("Cobertura de salud", "nomina.get_cobertura_salud_display"),
    ("Controles sanitarios", "nomina.get_controles_sanitarios_ultimo_anio_display"),
    ("Cal. vacunación al día", "nomina.get_calendario_vacunacion_al_dia_display"),
    ("Posee obra social", 'nomina.posee_obra_social|yesno:"Sí,No,—"'),
    ("Talla (cm)", "nomina.talla"),
    ("Peso (kg)", "nomina.peso"),
    ("Longitud acostado (cm)", "nomina.longitud_acostado"),
    ("Perímetro cefálico (cm)", "nomina.perimetro_cefalico"),
)

_CAMPOS_NUTRICION = (
    ("Lactancia", "nomina.get_lactancia_display"),
    ("Diagnóstico de peso", "nomina.get_diagnostico_peso_display"),
    ("Diagnóstico de talla", "nomina.get_diagnostico_talla_display"),
    ("Orientación MSAL", "nomina.get_orientacion_msal_display"),
)

_CAMPOS_ANSES = (
    ("AUH", "nomina.get_anses_auh_display"),
    ("AUE", "nomina.get_anses_aue_display"),
    ("ACSI", "nomina.get_anses_acsi_display"),
    ("ACN", "nomina.get_anses_acn_display"),
)

# ``badges``: (label, tone, display-list expression, truthy expression, spaced).
_VACUNAS = (
    ("bcg", "BCG"),
    ("neumococo", "Neumococo Conjugada"),
    ("quintuple", "Quíntuple o Pentavalente"),
    ("polio", "Polio (IPV o SALK)"),
    ("rotavirus", "Rotavirus"),
    ("meningococo", "Meningococo ACYW"),
    ("antigripal", "Antigripal"),
    ("hepatitis_a", "Hepatitis A"),
    ("triple_viral", "Triple Viral"),
    ("varicela", "Varicela"),
    ("triple_bacteriana_celular", "Triple Bacteriana Celular"),
    ("triple_bacteriana_acelular", "Triple Bacteriana Acelular"),
    ("sincicial_respiratorio", "Virus Sincicial Respiratorio"),
    ("fiebre_amarilla", "Fiebre Amarilla"),
)

_CULTURA_BADGES = (
    (
        "Grupos de pertenencia",
        "warning",
        "nomina.grupo_pertenencia_display",
        "nomina.grupo_pertenencia",
        True,
    ),
    ("Lenguajes", "info", "nomina.lenguajes_display", "nomina.lenguajes", False),
)
_DISCAPACIDAD_BADGES = (
    (
        "Tipo de discapacidad",
        "danger",
        "nomina.tipo_discapacidad_display",
        "nomina.tipo_discapacidad",
        False,
    ),
)
_NUTRICION_BADGES = (
    (
        "Alergias alimentarias",
        "warning",
        "nomina.alergias_alimentarias_display",
        "nomina.alergias_alimentarias",
        True,
    ),
)

_TEMPLATES = {}


def _plantilla(texto):
    if texto not in _TEMPLATES:
        _TEMPLATES[texto] = Template(texto)
    return _TEMPLATES[texto]


def _render(contexto, expresion):
    """``{{ expresion|default:"—" }}`` as the native ``_nomina_campo.html`` shows it."""
    plantilla = _plantilla("{{ " + expresion + '|default:"' + VACIO + '" }}')
    return plantilla.render(contexto)


def _valor(contexto, expresion):
    try:
        return Variable(expresion).resolve(contexto)
    except VariableDoesNotExist:
        return None


def _campos(contexto, campos, spaced=False):
    items = []
    for campo in campos:
        label, expresion = campo[0], campo[1]
        if len(campo) == 3 and _valor(contexto, campo[2]):
            texto = "No posee CUIL"
        else:
            texto = _render(contexto, expresion)
        items.append({"label": label, "value": texto})
    return {"kind": "fields", "items": items, "spaced": spaced}


def _chips(contexto, badges):
    bloques = []
    for label, tone, lista, condicion, spaced in badges:
        if _valor(contexto, condicion):
            items = [str(item) for item in _valor(contexto, lista) or ()]
            bloques.append(
                {
                    "kind": "badges",
                    "label": label,
                    "tone": tone,
                    "items": items,
                    "spaced": spaced,
                }
            )
    return bloques


def _seccion(key, icon, title, subtitle, bloques):
    return {
        "key": key,
        "icon": icon,
        "title": title,
        "subtitle": subtitle,
        "blocks": bloques,
    }


def _vacunas(contexto):
    vacunacion = _valor(contexto, "nomina.vacunacion_nomivac")
    if not vacunacion:
        return [{"kind": "vaccines", "rows": None}]
    local = Context({"vac": vacunacion}, autoescape=False)
    filas = [
        {
            "vaccine": nombre,
            "doses": _render(local, f"vac.{clave}.dosis"),
            "date": _render(local, f"vac.{clave}.fecha"),
        }
        for clave, nombre in _VACUNAS
        if _valor(local, f"vac.{clave}")
    ]
    return [{"kind": "vaccines", "rows": filas}]


def _secciones(contexto):
    nomina = contexto["nomina"]
    secciones = [
        _seccion(
            "registro",
            "fa-clipboard-list",
            "Registro",
            "Tipo de registro, fecha y referente del CDI",
            [_campos(contexto, _CAMPOS_REGISTRO)],
        ),
        _seccion(
            "nino",
            "fa-baby",
            "Datos del niño/a",
            "Identidad, documentación y sala",
            [_campos(contexto, _CAMPOS_NINO)],
        ),
        _seccion(
            "responsable1",
            "fa-user-shield",
            "Responsable 1",
            "Progenitor/a, tutor/a, curador/a o referente",
            [_campos(contexto, _CAMPOS_RESPONSABLE1)],
        ),
    ]
    if nomina.responsable_legal_2_relacion:
        secciones.append(
            _seccion(
                "responsable2",
                "fa-user-friends",
                "Responsable 2",
                None,
                [_campos(contexto, _CAMPOS_RESPONSABLE2)],
            )
        )
    secciones += [
        _seccion(
            "domicilio",
            "fa-home",
            "Domicilio principal",
            None,
            [_campos(contexto, _CAMPOS_DOMICILIO)],
        ),
        _seccion(
            "cultura",
            "fa-globe-americas",
            "Cultura e Identidad",
            None,
            [_campos(contexto, _CAMPOS_CULTURA, True)]
            + _chips(contexto, _CULTURA_BADGES),
        ),
        _seccion(
            "discapacidad",
            "fa-wheelchair",
            "Discapacidad",
            None,
            [_campos(contexto, _CAMPOS_DISCAPACIDAD, True)]
            + _chips(contexto, _DISCAPACIDAD_BADGES),
        ),
        _seccion(
            "salud",
            "fa-heartbeat",
            "Salud y Antropometría",
            None,
            [_campos(contexto, _CAMPOS_SALUD)],
        ),
        _seccion(
            "nutricion",
            "fa-apple-alt",
            "Nutrición y Asistencia ANSES",
            None,
            [_campos(contexto, _CAMPOS_NUTRICION, True)]
            + _chips(contexto, _NUTRICION_BADGES)
            + [
                {"kind": "rule"},
                {"kind": "caption", "text": "Asistencia ANSES"},
                _campos(contexto, _CAMPOS_ANSES),
            ],
        ),
        _seccion(
            "vacunacion", "fa-syringe", "Vacunación NOMIVAC", None, _vacunas(contexto)
        ),
    ]
    if nomina.observaciones:
        secciones.append(
            _seccion(
                "observaciones",
                "fa-comment-alt",
                "Observaciones",
                None,
                [{"kind": "text", "text": str(nomina.observaciones)}],
            )
        )
    return secciones


class PuedeVerCentros(BasePermission):
    """Same rule as the native ``permissions_any_required`` on the detail URL."""

    def has_permission(self, request, view):
        return _has_any_permissions(request.user, VER_CENTRO)


class NominaDestinatarioWebView(APIView):
    """``GET /api/web/cdi/centros/<pk>/nomina/<nomina_id>/``."""

    authentication_classes = [SessionAuthentication]
    permission_classes = [WebGatePermission, PuedeVerCentros]
    renderer_classes = [JSONRenderer]
    http_method_names = ["get", "head"]

    def get(self, request, pk, nomina_id):
        django_request = request._request  # pylint: disable=protected-access
        vista = NominaCentroInfanciaDestinatariosDetailView()
        vista.setup(django_request, pk=pk, nomina_id=nomina_id)
        try:
            vista.object = vista.get_object()
            context = vista.get_context_data()
        except Http404 as exc:
            raise NotFound() from exc
        nomina, centro = context["nomina"], context["centro"]
        contexto = Context({"nomina": nomina, "centro": centro}, autoescape=False)
        etiqueta = _plantilla("{{ nomina.apellido }}, {{ nomina.nombre }}").render(
            contexto
        )
        return Response(
            {
                "id": nomina.pk,
                "label": etiqueta,
                "centro": {
                    "id": centro.pk,
                    "nombre": str(centro.nombre),
                    "url": reverse("centrodeinfancia_nomina_ver", args=[centro.pk]),
                },
                "editar_url": (
                    reverse(
                        "centrodeinfancia_nomina_editar", args=[centro.pk, nomina.pk]
                    )
                    if context["puede_editar"]
                    else None
                ),
                "sections": _secciones(contexto),
                "messages": pending_messages(django_request),
            }
        )
