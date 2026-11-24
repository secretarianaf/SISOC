"""Web API (G1 v1) of the CDI worker detail (CDI05) for the React page.

``GET /api/web/cdi/centros/<pk>/trabajadores/<trabajador_id>/`` runs
``TrabajadorCentroInfanciaDetailView`` itself (the worker is looked up in the
actor's scope and inside the nested centre, 404 otherwise) and projects each
field of ``trabajador_detail.html`` with the same template expression as the
native page (``{{ expr|default:"—" }}``), so choice labels, localized dates and
the CUIL flag come out identical. The permission is the one of the native URL
(``centrodeinfancia.view_trabajador``, superuser bypass included). Read-only:
GET and HEAD only; the edit and delete controls follow the native flags and
the delete goes through the existing ``trabajador_eliminar_web`` endpoint.
"""

from django.http import Http404
from django.template import Context
from django.urls import reverse
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import NotFound
from rest_framework.permissions import BasePermission
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.views import APIView

from centrodeinfancia.views import TrabajadorCentroInfanciaDetailView
from centrodeinfancia.web_api import pending_messages
from centrodeinfancia.web_api_nomina import (
    _campos,
    _plantilla,
    _seccion,
    _valor,
)
from core.decorators import _has_any_permissions
from core.web_gate import WebGatePermission

VER_TRABAJADOR = ["centrodeinfancia.view_trabajador"]

_CAMPOS_INSTITUCION = (
    ("Jurisdicción", "centro.provincia"),
    ("Departamento", "centro.departamento"),
    ("Localidad", "centro.localidad"),
    ("Municipio", "centro.municipio"),
    ("Nombre del CDI", "centro.nombre"),
    ("Código CDI", "centro.codigo_cdi"),
    ("Fecha de carga", "trabajador.fecha_carga"),
)

_CAMPOS_FUERZA = (
    ("Subcomponente", "trabajador.get_subcomponente_display"),
    ("Función (EGP)", "trabajador.get_funcion_egp_display"),
    ("Función (CDI)", "trabajador.get_funcion_cdi_display"),
    ("Sala (CDI)", "trabajador.get_sala_cdi_display"),
    ("Apellido", "trabajador.apellido"),
    ("Nombre", "trabajador.nombre"),
    ("Fecha de nacimiento", "trabajador.fecha_nacimiento"),
    ("Edad", "trabajador.edad"),
    ("Sexo registral", "trabajador.get_sexo_registral_display"),
    ("Tipo de documentación", "trabajador.get_tipo_documentacion_display"),
    ("DNI", "trabajador.dni"),
    ("CUIT", "trabajador.cuit", "trabajador.sin_cuil"),
    ("País de nacimiento", "trabajador.pais_nacimiento"),
    ("Nacionalidad", "trabajador.nacionalidad_trabajador"),
)

_CAMPOS_FORMACION = (
    ("Nivel educativo", "trabajador.get_nivel_educativo_display"),
    ("Formación académica", "trabajador.get_formacion_academica_display"),
    (
        "Años de trabajo en primera infancia",
        "trabajador.get_anos_trabajo_primera_infancia_display",
    ),
)

_CAMPOS_CONTRATACION = (
    ("Tipo de contratación", "trabajador.get_tipo_contratacion_display"),
    ("Carga horaria semanal (horas)", "trabajador.carga_horaria_semanal"),
)

_CAMPOS_CONTACTO = (
    ("Correo electrónico", "trabajador.email"),
    ("Teléfono celular", "trabajador.telefono"),
    ("Calle y numeración", "trabajador.calle_contacto"),
    ("Unidad funcional", "trabajador.unidad_funcional"),
    ("Tipo de barrio", "trabajador.get_tipo_barrio_display"),
    ("Jurisdicción", "trabajador.provincia_contacto"),
    ("Municipio", "trabajador.municipio_contacto"),
    ("Localidad", "trabajador.localidad_contacto"),
)

_CAMPOS_IDENTIDAD = (
    ("Pueblo originario", "trabajador.get_pueblo_originario_display"),
    ("¿Es intérprete?", "trabajador.get_es_interprete_display"),
)

_CAMPOS_DISCAPACIDAD = (
    ("¿Tiene discapacidad?", "trabajador.get_tiene_discapacidad_display"),
    ("¿Recibe apoyo?", "trabajador.get_recibe_apoyo_discapacidad_display"),
    ("¿Tiene CUD?", "trabajador.get_tiene_cud_display"),
    ("Número de CUD", "trabajador.numero_cud"),
)


def _chips(contexto, spec):
    """The badge list of a section; its last item is the native wrapper class."""
    label, tone, lista, condicion, wrapper = spec
    if not _valor(contexto, condicion):
        return []
    return [
        {
            "kind": "badges",
            "label": label,
            "tone": tone,
            "items": [str(item) for item in _valor(contexto, lista) or ()],
            "wrapper": wrapper,
        }
    ]


def _secciones(contexto):
    return [
        _seccion(
            "institucion",
            "fa-building",
            "Institución",
            "Datos del CDI y fecha de carga",
            [_campos(contexto, _CAMPOS_INSTITUCION)],
        ),
        _seccion(
            "fuerza_trabajo",
            "fa-id-card",
            "Fuerza de trabajo",
            "Rol, función y datos personales",
            [_campos(contexto, _CAMPOS_FUERZA)],
        ),
        _seccion(
            "formacion",
            "fa-graduation-cap",
            "Formación y experiencia",
            "Nivel educativo, capacitaciones y trayectoria",
            [_campos(contexto, _CAMPOS_FORMACION)]
            + _chips(
                contexto,
                (
                    "Capacitaciones certificadas (últimos tres años)",
                    "warning",
                    "trabajador.capacitaciones_certificadas_display",
                    "trabajador.capacitaciones_certificadas",
                    "mt-3",
                ),
            ),
        ),
        _seccion(
            "contratacion",
            "fa-file-contract",
            "Contratación",
            "Tipo de contrato y carga horaria",
            [_campos(contexto, _CAMPOS_CONTRATACION)],
        ),
        _seccion(
            "contacto",
            "fa-phone",
            "Contacto",
            "Datos de contacto y domicilio",
            [_campos(contexto, _CAMPOS_CONTACTO)],
        ),
        _seccion(
            "identidad",
            "fa-globe-americas",
            "Cultura e identidad",
            "Pertenencia, lenguajes e interculturalidad",
            [_campos(contexto, _CAMPOS_IDENTIDAD, True)]
            + _chips(
                contexto,
                (
                    "Grupos de pertenencia",
                    "warning",
                    "trabajador.grupo_pertenencia_display",
                    "trabajador.grupo_pertenencia",
                    "mb-3",
                ),
            )
            + _chips(
                contexto,
                (
                    "Lenguajes",
                    "info",
                    "trabajador.lenguajes_display",
                    "trabajador.lenguajes",
                    "",
                ),
            ),
        ),
        _seccion(
            "discapacidad",
            "fa-heartbeat",
            "Discapacidad",
            "Condición, apoyos y CUD",
            [_campos(contexto, _CAMPOS_DISCAPACIDAD, True)]
            + _chips(
                contexto,
                (
                    "Tipo de discapacidad",
                    "danger",
                    "trabajador.tipo_discapacidad_display",
                    "trabajador.tipo_discapacidad",
                    "",
                ),
            ),
        ),
    ]


class PuedeVerTrabajadores(BasePermission):
    """Same rule as the native ``permissions_any_required`` on the detail URL."""

    def has_permission(self, request, view):
        return _has_any_permissions(request.user, VER_TRABAJADOR)


class TrabajadorDetalleWebView(APIView):
    """``GET /api/web/cdi/centros/<pk>/trabajadores/<trabajador_id>/``."""

    authentication_classes = [SessionAuthentication]
    permission_classes = [WebGatePermission, PuedeVerTrabajadores]
    renderer_classes = [JSONRenderer]
    http_method_names = ["get", "head"]

    def get(self, request, pk, trabajador_id):
        django_request = request._request  # pylint: disable=protected-access
        vista = TrabajadorCentroInfanciaDetailView()
        vista.setup(django_request, pk=pk, trabajador_id=trabajador_id)
        try:
            vista.object = vista.get_object()
            context = vista.get_context_data()
        except Http404 as exc:
            raise NotFound() from exc
        trabajador, centro = context["trabajador"], context["centro"]
        contexto = Context(
            {"trabajador": trabajador, "centro": centro}, autoescape=False
        )
        etiqueta = _plantilla(
            "{{ trabajador.apellido }}, {{ trabajador.nombre }}"
        ).render(contexto)
        args = [centro.pk, trabajador.pk]
        return Response(
            {
                "id": trabajador.pk,
                "label": etiqueta,
                "centro": {
                    "id": centro.pk,
                    "nombre": str(centro.nombre),
                    "url": reverse("centrodeinfancia_detalle", args=[centro.pk]),
                },
                "editar_url": (
                    reverse("centrodeinfancia_trabajador_editar", args=args)
                    if context["puede_editar_trabajadores"]
                    else None
                ),
                "eliminar_url": (
                    f"/api/web/cdi/centros/{centro.pk}/trabajadores/{trabajador.pk}/eliminar/"
                    if context["puede_eliminar_trabajadores"]
                    else None
                ),
                "sections": _secciones(contexto),
                "messages": pending_messages(django_request),
            }
        )
