"""Web API (G1 v1) of the CDI institutional form list and detail (CDI03) for React.

``GET /api/web/cdi/centros/<pk>/formularios/`` and
``GET /api/web/cdi/centros/<pk>/formularios/<form_pk>/`` run
``FormularioCDIListView`` and ``FormularioCDIDetailView`` themselves (the centre
and the form come from the actor's scope, 404 outside it; an invalid page is a
404), and project each cell with the same template expression as
``formulario_cdi_list.html`` and ``formulario_cdi_detail.html`` so localized
dates, decimals, choice labels and the ``-`` placeholder are the native ones.
The permission is the one of the native URLs (``view_formulariocdi``, superuser
bypass included). Read-only: GET and HEAD only; the "Nuevo formulario" and
"Editar" links keep the native URLs (the form itself is
``web_api_formulario_form``).
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

from centrodeinfancia.views_formulario_cdi import (
    FormularioCDIDetailView,
    FormularioCDIListView,
)
from centrodeinfancia.web_api import pending_messages
from centrodeinfancia.web_api_nomina import _plantilla
from core.decorators import _has_any_permissions
from core.web_gate import WebGatePermission

VER_FORMULARIO = ["centrodeinfancia.view_formulariocdi"]
GUION = "-"


def _r(contexto, expresion, por_defecto=None):
    """``{{ expresion|default:"-" }}`` (or the bare expression) as the native page shows it."""
    filtro = f'|default:"{por_defecto}"' if por_defecto is not None else ""
    return _plantilla("{{ " + expresion + filtro + " }}").render(contexto)


class PuedeVerFormularios(BasePermission):
    """Same rule as the native ``permissions_any_required`` on both URLs."""

    def has_permission(self, request, view):
        return _has_any_permissions(request.user, VER_FORMULARIO)


def _centro(centro):
    return {
        "id": centro.pk,
        "nombre": str(centro.nombre),
        "url": reverse("centrodeinfancia_detalle", args=[centro.pk]),
    }


def _pagina(pagina, rango):
    return {
        "is_paginated": pagina is not None and pagina.has_other_pages(),
        "number": pagina.number if pagina else 1,
        "count": pagina.paginator.count if pagina else 0,
        "previous": (
            pagina.previous_page_number() if pagina and pagina.has_previous() else None
        ),
        "next": pagina.next_page_number() if pagina and pagina.has_next() else None,
        "range": [item if isinstance(item, int) else "…" for item in rango],
    }


class FormularioListaWebView(APIView):
    """``GET /api/web/cdi/centros/<pk>/formularios/``."""

    authentication_classes = [SessionAuthentication]
    permission_classes = [WebGatePermission, PuedeVerFormularios]
    renderer_classes = [JSONRenderer]
    http_method_names = ["get", "head"]

    def get(self, request, pk):
        django_request = request._request  # pylint: disable=protected-access
        vista = FormularioCDIListView()
        vista.setup(django_request, pk=pk)
        try:
            vista.object_list = vista.get_queryset()
            context = vista.get_context_data()
        except Http404 as exc:
            raise NotFound() from exc
        filas = []
        for item in context["summary_items"]:
            ctx = Context({"item": item}, autoescape=False)
            filas.append(
                {
                    "id": item["id"],
                    "codigo": _r(ctx, "item.id_codigo_cdi")
                    + " / "
                    + _r(ctx, "item.id"),
                    "fecha": _r(ctx, 'item.fecha_relevamiento|date:"d/m/Y"', GUION),
                    "respondente": _r(ctx, "item.nombre_completo_respondente", GUION),
                    "creado": _r(ctx, 'item.created_at|date:"d/m/Y H:i"'),
                    "actualizado": _r(ctx, 'item.updated_at|date:"d/m/Y H:i"'),
                    "ver_url": item["detail_url"],
                    "editar_url": item["edit_url"],
                }
            )
        return Response(
            {
                "centro": _centro(context["centro"]),
                "crear_url": reverse(
                    "centrodeinfancia_formulario_crear", args=[context["centro"].pk]
                ),
                "rows": filas,
                "page": _pagina(
                    context.get("page_obj"), context.get("page_range") or ()
                ),
                "messages": pending_messages(django_request),
            }
        )


def _tabla(filas, columnas):
    """Rows of cells rendered with the template expression of each column."""
    return [
        [
            _r(Context({"row": fila}, autoescape=False), expresion, GUION)
            for expresion in columnas
        ]
        for fila in filas
    ]


class FormularioDetalleWebView(APIView):
    """``GET /api/web/cdi/centros/<pk>/formularios/<form_pk>/``."""

    authentication_classes = [SessionAuthentication]
    permission_classes = [WebGatePermission, PuedeVerFormularios]
    renderer_classes = [JSONRenderer]
    http_method_names = ["get", "head"]

    def get(self, request, pk, form_pk):
        django_request = request._request  # pylint: disable=protected-access
        vista = FormularioCDIDetailView()
        vista.setup(django_request, pk=pk, form_pk=form_pk)
        try:
            vista.object = vista.get_object()
            context = vista.get_context_data()
        except Http404 as exc:
            raise NotFound() from exc
        formulario, centro = context["formulario"], context["centro"]
        ctx = Context({"formulario": formulario}, autoescape=False)
        totales = Context({"t": context["totales_salas"]}, autoescape=False)
        creador = formulario.created_by
        return Response(
            {
                "id": formulario.pk,
                "centro": _centro(centro),
                "codigo_cdi": _r(ctx, "formulario.codigo_cdi", GUION),
                "creado": _r(ctx, 'formulario.created_at|date:"d/m/Y H:i"'),
                "creado_por": (
                    _r(
                        Context({"u": creador}, autoescape=False),
                        "u.get_full_name",
                        creador.username,
                    )
                    if creador
                    else None
                ),
                "editar_url": reverse(
                    "centrodeinfancia_formulario_editar",
                    args=[centro.pk, formulario.pk],
                ),
                "sections": [
                    {
                        "title": str(seccion["title"]),
                        "items": [
                            {"label": str(i["label"]), "value": str(i["value"])}
                            for i in seccion["items"]
                        ],
                    }
                    for seccion in context["detail_sections"]
                ],
                "horarios": _tabla(
                    context["horarios_funcionamiento"],
                    (
                        "row.get_dia_display",
                        'row.hora_apertura|time:"H:i"',
                        'row.hora_cierre|time:"H:i"',
                    ),
                ),
                "salas": {
                    "rows": _tabla(
                        context["filas_salas"],
                        (
                            "row.get_grupo_etario_display",
                            "row.cantidad_salas",
                            "row.superficie_exclusiva_m2",
                            "row.cantidad_ninos",
                            "row.cantidad_personal_sala",
                            "row.personal_por_sala",
                        ),
                    ),
                    "totales": [
                        _r(totales, f"t.{campo}")
                        for campo in (
                            "cantidad_salas",
                            "superficie_exclusiva_m2",
                            "cantidad_ninos",
                            "cantidad_personal_sala",
                        )
                    ],
                },
                "demanda": {
                    "rows": _tabla(
                        context["filas_demanda_insatisfecha"],
                        (
                            "row.get_grupo_etario_display",
                            "row.cantidad_demanda_insatisfecha",
                        ),
                    ),
                    "total": str(context["total_demanda_insatisfecha"]),
                },
                "articulacion": _tabla(
                    context["filas_articulacion"],
                    ("row.get_tipo_institucion_display", "row.get_frecuencia_display"),
                ),
                "messages": pending_messages(django_request),
            }
        )
