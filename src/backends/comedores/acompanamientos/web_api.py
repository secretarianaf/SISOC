"""Web API (G1 v1) of the acompañamiento follow-up and milestones (AC01).

``/api/web/comedores/`` is published by the comedores backend (``url_prefixes``
in ``src/backends/config/backends.json``). In a split deploy the core checks the
session and the web prerequisites and signs each request; the runtime only
serves requests its ``WebGateMiddleware`` verified. In the monolith
``WebGatePermission`` evaluates the same policy locally. After that the native
route guards apply unchanged (superuser bypass included):

- list and detail: ``permissions_any_required(["acompanamientos.view_informacionrelevante"])``;
- restore a milestone: ``permissions_all_required(["auth.role_tecnico_comedor",
  "acompanamientos.change_hitos"])``.

List and detail run the native views themselves (``setup()``, queryset, scope,
filters, ordering, column preferences, pagination and context), so they cannot
drift from the HTML pages; this module only projects that context to JSON. The
CSV export stays the native GET ``/acompanamientos/acompanamiento/exportar/``.

Restoring a milestone repeats the native ``restaurar_hito`` steps (scope 404,
milestones of the shown agreement, ``False`` and ``save()``, native messages)
with two agent decisions recorded in the AC01 contract: the shown
``admision_id`` is explicit (no Referer fallback) and ``campo`` only accepts
the 23 boolean milestones the page lists. The native view stays as it is.
"""

from django.contrib import messages
from django.http import Http404
from django.template import Context, Template
from django.urls import reverse
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import NotFound
from rest_framework.permissions import BasePermission
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.views import APIView

# The exact predicates of the native URL decorators.
from core.decorators import _has_all_permissions, _has_any_permissions
from core.pagination import build_compact_page_range
from core.templatetags.custom_filters import has_any_perm
from core.web_gate import WebGatePermission
from acompanamientos.acompanamiento_service import AcompanamientoService
from acompanamientos.views import (
    AcompanamientoDetailView,
    ComedoresAcompanamientoListView,
    _build_detalle_acompanamiento_url,
    _parse_admision_id,
)
from comedores.services.comedor_service import ComedorService

VIEW_PERMISSIONS = ["acompanamientos.view_informacionrelevante"]
RESTORE_PERMISSIONS = ["auth.role_tecnico_comedor", "acompanamientos.change_hitos"]
# ``search_bar.html`` default ``export_permissions``.
EXPORT_BUTTON_PERMISSIONS = "auth.role_exportar_a_csv"
MESSAGE_LEVELS = {
    messages.DEBUG: "info",
    messages.INFO: "info",
    messages.SUCCESS: "success",
    messages.WARNING: "warning",
    messages.ERROR: "error",
}
NO_HITOS = "No se encontraron hitos para el convenio seleccionado."
_UPPER = Template("{{ valor|upper }}")
_INFO = {
    "expediente": Template('{{ info.expediente_nro |default:"-" }}'),
    "if_relevamiento": Template('{{ info.if_relevamiento|default:"-" }}'),
    "vencimiento": Template(
        "{{ info.fecha_vencimiento_mandatos|date:'d/m/Y'|default_if_none:\"—\" }}"
    ),
}


class VerAcompanamiento(BasePermission):
    def has_permission(self, request, view):
        return _has_any_permissions(request.user, VIEW_PERMISSIONS)


class RestaurarHito(BasePermission):
    def has_permission(self, request, view):
        return _has_all_permissions(request.user, RESTORE_PERMISSIONS)


class _WebView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [WebGatePermission, VerAcompanamiento]
    renderer_classes = [JSONRenderer]
    http_method_names = ["get", "head"]


def pending_messages(request):
    """Consume queued Django messages exactly as the native page would."""
    return [
        {"message": str(m), "level": MESSAGE_LEVELS.get(m.level, "info")}
        for m in messages.get_messages(request)
    ]


def _native(view_class, request, **kwargs):
    view = view_class()
    view.setup(request._request, **kwargs)  # pylint: disable=protected-access
    return view


def _render(template, **context):
    return template.render(Context(context)).strip()


def _query_prefix(request, query):
    """Link prefix of ``components/pagination.html`` (``busqueda`` first)."""
    prefix = f"busqueda={_urlencode(query)}&" if query else ""
    return prefix + "".join(
        f"{clave}={_urlencode(valor)}&"
        for clave, valor in request.GET.items()
        if clave not in ("page", "busqueda")
    )


def _urlencode(value):
    return _render(Template("{{ v|urlencode }}"), v=value)


def _header(header):
    payload = {"title": str(header["title"]), "sort_url": None, "sort_direction": None}
    if header.get("sort_url"):
        payload["sort_url"] = header["sort_url"]
        payload["sort_direction"] = header.get("sort_direction")
    return payload


class AcompanamientosListWebView(_WebView):
    """``GET /api/web/comedores/acompanamientos/``: ``lista_comedores.html``."""

    def get(self, request):
        vista = _native(ComedoresAcompanamientoListView, request)
        try:
            vista.object_list = vista.get_queryset()
            context = vista.get_context_data()
        except Http404 as exc:
            raise NotFound() from exc
        page = context["page_obj"]
        user = request.user
        return Response(
            {
                "filters_config": context["filters_config"],
                "favorites": {
                    "section": context["seccion_filtros_favoritos"],
                    "url": reverse("filtros_favoritos"),
                    "detail_url_template": reverse(
                        "detalle_filtro_favorito", kwargs={"pk": 0}
                    ),
                },
                "urls": {
                    "list": context["filters_action"],
                    "reset": context["reset_url"],
                    "export": reverse("lista_comedores_acompanamiento_exportar"),
                },
                "can_export": user.is_superuser
                or has_any_perm(user, EXPORT_BUTTON_PERMISSIONS),
                "columns": context["column_config"],
                "headers": [_header(h) for h in context["table_headers"]],
                "results": [
                    {
                        "cells": [
                            {
                                "content": str(cell["content"]),
                                "data_attr": cell.get("data_attr"),
                                "data_value": cell.get("data_value"),
                            }
                            for cell in item["cells"]
                        ],
                        "actions": [
                            {
                                "label": action["label"],
                                "url": action["url"],
                                "type": action["type"],
                            }
                            for action in item["actions"]
                        ],
                    }
                    for item in context["comedores"]
                ],
                "page": {
                    "is_paginated": context["is_paginated"],
                    "number": page.number,
                    "count": page.paginator.count,
                    "has_rows": len(page.object_list) > 0,
                    "previous": (
                        page.previous_page_number() if page.has_previous() else None
                    ),
                    "next": page.next_page_number() if page.has_next() else None,
                    "range": [
                        "…" if numero in ("...", "…") else numero
                        for numero in build_compact_page_range(page)
                    ],
                    "query_without_page": _query_prefix(request, context["query"]),
                },
                "messages": pending_messages(request),
            }
        )


def _convenio(admision, activa_id):
    acompanamiento = getattr(admision, "acompanamiento", None)
    numero = acompanamiento.nro_convenio if acompanamiento else ""
    return {
        "id": admision.pk,
        "label": numero or f"Admisión #{admision.pk}",
        "activa": admision.activa,
        "seleccionada": admision.pk == activa_id,
    }


def _info(context):
    info = context["info_relevante"]
    if not info:
        return None
    return {
        "nro_convenio": context["nro_convenio"] or "",
        "expediente": _render(_INFO["expediente"], info=info),
        "disposicion": context["numero_disposicion"] or "-",
        "if_relevamiento": _render(_INFO["if_relevamiento"], info=info),
        "vencimiento": _render(_INFO["vencimiento"], info=info),
        "codigo_proyecto": context["comedor"].codigo_de_proyecto or "-",
    }


def _sin_informacion(valor):
    return "Sin información" if valor is None else str(valor)


DIAS = ("lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo")


def _prestaciones(context):
    return {
        "dias": [str(dia) for dia in context["dias_semana"]],
        "por_dia": [
            {
                "tipo": _render(_UPPER, valor=fila.get("tipo")),
                "valores": [_sin_informacion(fila.get(dia)) for dia in DIAS],
            }
            for fila in context["prestaciones_por_dia"]
        ],
        "semanal": [
            {
                "tipo": _render(_UPPER, valor=fila.get("tipo")),
                "cantidad": str(fila.get("cantidad")),
            }
            for fila in context["prestaciones_dias"]
        ],
    }


def _hitos(context):
    hitos = context["hitos"]
    if not hitos:
        return None
    fechas = context["fechas_hitos"]
    return [
        {
            "campo": item["campo"],
            "descripcion": item["descripcion"],
            "completado": bool(getattr(hitos, item["campo"])),
            "fecha": fechas.get(item["campo"]) or "—",
        }
        for item in context["hitos_config"]
    ]


class AcompanamientoDetailWebView(_WebView):
    """``GET /api/web/comedores/acompanamientos/<comedor_id>/``: the native ficha."""

    def get(self, request, comedor_id):
        vista = _native(AcompanamientoDetailView, request, comedor_id=comedor_id)
        try:
            vista.object = vista.get_object()
        except Http404 as exc:
            raise NotFound() from exc
        context = vista.get_context_data(object=vista.object)
        comedor = context["comedor"]
        activa_id = context["admision_id_activa"]
        informe = context["informe_tecnico_complementario"]
        consulta = f"?admision_id={activa_id}" if activa_id else ""
        return Response(
            {
                "comedor": {"id": comedor.pk, "nombre": comedor.nombre},
                "admision_id": activa_id,
                "convenios": [
                    _convenio(adm, activa_id)
                    for adm in context["admisiones_disponibles"]
                ],
                "multiples_activos": context["tiene_multiples_activos"],
                "informacion": _info(context),
                "prestaciones": _prestaciones(context),
                "hitos": _hitos(context),
                "puede_restaurar": context["es_tecnico_comedor"],
                "urls": {
                    "detalle": reverse("detalle_acompanamiento", args=[comedor.pk]),
                    "intervenciones": reverse(
                        "comedor_intervencion_ver", args=[comedor.pk]
                    )
                    + consulta,
                    "expedientes": reverse("expedientespagos_list", args=[comedor.pk]),
                    "seguimiento": reverse(
                        "rendicioncuentasmensual_list", args=[comedor.pk]
                    ),
                    "informe_complementario": (
                        reverse(
                            "informe_complementario_ver",
                            kwargs={"tipo": informe.tipo, "pk": informe.pk},
                        )
                        + "?origen=acompanamiento"
                        if informe
                        else None
                    ),
                    "comedor": reverse("comedor_detalle", args=[comedor.pk]),
                    "restaurar": reverse(
                        "acompanamientos_web_restaurar_hito", args=[comedor.pk]
                    ),
                },
                "messages": pending_messages(request),
            }
        )


# The 23 boolean milestones of ``acompañamiento_detail.html`` (``hitos_config``).
HITOS_CAMPOS = frozenset(
    (
        "retiro_tarjeta",
        "habilitacion_tarjeta",
        "alta_usuario_plataforma",
        "capacitacion_realizada",
        "capacitacion_fch_realizada",
        *(f"notificacion_acreditacion_{n}" for n in range(1, 7)),
        "nomina_entregada_inicial",
        *(f"nomina_alta_baja_{n}" for n in range(2, 7)),
        *(f"certificado_prestaciones_{n}" for n in range(1, 7)),
    )
)


def _rechazo(status, texto, redirect):
    return Response(
        {
            "ok": False,
            "message": {"level": "error", "text": texto},
            "redirect": redirect,
        },
        status=status,
    )


class RestaurarHitoWebView(APIView):
    """``POST /api/web/comedores/acompanamientos/<comedor_id>/hitos/restaurar/``."""

    authentication_classes = [SessionAuthentication]
    permission_classes = [WebGatePermission, RestaurarHito]
    renderer_classes = [JSONRenderer]
    http_method_names = ["post"]

    def post(self, request, comedor_id):
        campo = request.POST.get("campo", "")
        admision_id = _parse_admision_id(request.POST.get("admision_id"))
        try:
            comedor = ComedorService.get_scoped_comedor_or_404(comedor_id, request.user)
        except Http404 as exc:
            raise NotFound() from exc
        redirect = _build_detalle_acompanamiento_url(comedor_id, admision_id)
        hito = AcompanamientoService.obtener_hitos(comedor, admision_id=admision_id)
        if not hito:
            return _rechazo(409, NO_HITOS, redirect)
        if campo not in HITOS_CAMPOS:
            return _rechazo(
                400, f"El campo '{campo}' no existe en el modelo Hitos.", redirect
            )
        setattr(hito, campo, False)
        hito.save()
        texto = f"El campo '{campo}' ha sido restaurado correctamente."
        # The detail page shows it, as after the native redirect.
        messages.success(request._request, texto)  # pylint: disable=protected-access
        return Response(
            {
                "ok": True,
                "message": {"level": "success", "text": texto},
                "redirect": redirect,
            }
        )
