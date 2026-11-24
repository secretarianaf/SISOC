"""Web API (G1 v1) of the CDI nómina list (CDI04.02/CDI04.03) for the React page.

``/api/web/cdi/`` is published by this backend. In a split deploy the core
checks the session and the web prerequisites and signs each request; the
runtime only serves what its ``WebGateMiddleware`` verified. In the monolith
``WebGatePermission`` evaluates the same policy locally. After that the native
URL guards apply unchanged:

* list: ``centrodeinfancia.view_nominacentroinfancia`` (same predicate as
  ``permissions_any_required``, superuser bypass included);
* derivation: ``change_nominacentroinfancia`` OR ``add_nominacentroinfancia``,
  exactly the decorator of ``centrodeinfancia_nomina_derivar``.

The list runs ``NominaCentroInfanciaDetailView`` itself (scoped centre, scoped
rows of 100, global metrics, centres to derive to), so scope and numbers
cannot drift from the HTML page. Every cell is rendered with the same
template expression as ``nomina_detail.html``. The derivation POST calls the
native ``nomina_centrodeinfancia_derivar`` function unchanged (domain service,
status codes and messages included); it only adds the G1 gate, the permission
and CSRF in front of it. Edit, create and delete stay native links.
"""

from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.template import Context, Template
from django.urls import reverse
from django.utils import formats
from django.utils.cache import patch_cache_control, patch_vary_headers
from django.views.decorators.csrf import csrf_protect
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import NotFound
from rest_framework.permissions import BasePermission
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.views import APIView

from centrodeinfancia.views import (
    NominaCentroInfanciaDetailView,
    nomina_centrodeinfancia_derivar,
)
from centrodeinfancia.web_api import pending_messages
from centrodeinfancia.web_api_observaciones import SIN_PERMISO, _gate, _json
from core.decorators import _has_any_permissions, permissions_any_required
from core.web_gate import WebGatePermission

VER_NOMINA = ["centrodeinfancia.view_nominacentroinfancia"]
DERIVAR = [
    "centrodeinfancia.change_nominacentroinfancia",
    "centrodeinfancia.add_nominacentroinfancia",
]

_TEMPLATES = {}

# Expressions of each row cell, as written in ``nomina_detail.html``.
_CELDAS = {
    "fecha": '{{ e.fecha|date:"d/m/Y" }}',
    "nombre": (
        "{{ e.apellido|default:e.ciudadano.apellido }}, "
        "{{ e.nombre|default:e.ciudadano.nombre }}"
    ),
    "dni": '{{ e.dni|default:e.ciudadano.documento|default:"-" }}',
    # ``firstof``: with no sex on the record nor on the citizen, ``default:`` raised (#2925).
    "sexo": '{% firstof e.sexo e.ciudadano.sexo.sexo "-" %}',
    "edad": '{{ e.edad|default:e.ciudadano.edad|default:"-" }}',
    "sala": '{{ e.sala|default:"-" }}',
    "sala_filtro": "{{ e.sala|default:'' }}",
    "derivar_nombre": "{{ e.nombre }} {{ e.apellido }}",
}


class PuedeVerNomina(BasePermission):
    """Same rule as the native ``permissions_any_required`` on the list URL."""

    def has_permission(self, request, view):
        return _has_any_permissions(request.user, VER_NOMINA)


def _render(expresion, contexto):
    if expresion not in _TEMPLATES:
        _TEMPLATES[expresion] = Template(expresion)
    return _TEMPLATES[expresion].render(contexto)


def _entero(valor):
    """``{{ n|default:0 }}``: localized like the template prints it."""
    return str(formats.localize(valor or 0))


def _fila(registro, centro):
    contexto = Context({"e": registro}, autoescape=False)
    estado = registro.estado if registro.estado in ("activo", "pendiente") else "baja"
    celdas = {clave: _render(expr, contexto) for clave, expr in _CELDAS.items()}
    return {
        "id": registro.pk,
        "estado": estado,
        "sala_filtro": celdas["sala_filtro"],
        "fecha": celdas["fecha"],
        "nombre": celdas["nombre"],
        "ciudadano_url": reverse("ciudadanos_ver", args=[registro.ciudadano_id]),
        "dni": celdas["dni"],
        "sexo": celdas["sexo"],
        "edad": celdas["edad"],
        "sala": celdas["sala"],
        "derivar_nombre": celdas["derivar_nombre"],
        "urls": {
            "ver": reverse(
                "centrodeinfancia_nomina_destinatario_ver",
                args=[centro.pk, registro.pk],
            ),
            "editar": reverse(
                "centrodeinfancia_nomina_editar", args=[centro.pk, registro.pk]
            ),
            "borrar": reverse(
                "centrodeinfancia_nomina_borrar", args=[centro.pk, registro.pk]
            ),
        },
    }


def _rango(rangos, clave):
    return {
        "num": _entero(rangos[clave]),
        "pct": _entero(rangos[f"pct_{clave}"]),
        "width": int(rangos[f"pct_{clave}"] or 0),
        "zero": not rangos[clave],
    }


class NominaListaWebView(APIView):
    """``GET /api/web/cdi/centros/<pk>/nomina/``: metrics, rows and derive targets."""

    authentication_classes = [SessionAuthentication]
    permission_classes = [WebGatePermission, PuedeVerNomina]
    renderer_classes = [JSONRenderer]
    http_method_names = ["get", "head"]

    def get(self, request, pk):
        django_request = request._request  # pylint: disable=protected-access
        vista = NominaCentroInfanciaDetailView()
        vista.setup(django_request, pk=pk)
        try:
            vista.object_list = vista.get_queryset()
            context = vista.get_context_data()
        except Http404 as exc:
            raise NotFound() from exc
        centro, pagina = context["object"], context["nomina"]
        rangos = context["nomina_rangos"]
        contexto = Context({"object": centro}, autoescape=False)
        return Response(
            {
                "centro": {
                    "id": centro.pk,
                    "nombre": str(centro.nombre),
                    "url": reverse("centrodeinfancia_detalle", args=[centro.pk]),
                    "codigo_cdi": str(centro.codigo_cdi or ""),
                    "ubicacion": _render(
                        '{{ object.localidad|default:"-" }}, '
                        '{{ object.provincia|default:"-" }}',
                        contexto,
                    ),
                },
                "stats": {
                    "asistentes": _entero(context["cantidad_nomina"]),
                    "hombres": _entero(context["nominaM"]),
                    "mujeres": _entero(context["nominaF"]),
                    "x": _entero(context["nominaX"]),
                    "menores": _entero(context["menores"]),
                    "espera": _entero(context["espera"]),
                },
                "rangos": {
                    clave: _rango(rangos, clave)
                    for clave in (
                        "ninos",
                        "adolescentes",
                        "adultos",
                        "adultos_mayores",
                        "adulto_mayor_avanzado",
                    )
                },
                "rows": [_fila(registro, centro) for registro in pagina],
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
                "centros_para_derivar": [
                    {"id": c["id"], "nombre": str(c["nombre"])}
                    for c in context["centros_para_derivar"]
                ],
                "urls": {
                    "lista": reverse("centrodeinfancia"),
                    "crear": reverse("centrodeinfancia_nomina_crear", args=[centro.pk]),
                },
                "messages": pending_messages(django_request),
            }
        )


@csrf_protect
def nomina_derivar_web(request, pk):
    """``POST /api/web/cdi/nomina/<pk>/derivar/``: the native derivation, as is."""
    response = _gate(request)
    if response is not None:
        return response
    guarded = permissions_any_required(DERIVAR)(nomina_centrodeinfancia_derivar)
    try:
        response = guarded(request, pk=pk)
    except PermissionDenied as exc:
        return _json({"detail": str(exc) or SIN_PERMISO}, 403)
    except Http404:
        return _json({"detail": "No encontrado."}, 404)
    patch_cache_control(response, private=True, no_store=True)
    patch_vary_headers(response, ("Cookie",))
    return response
