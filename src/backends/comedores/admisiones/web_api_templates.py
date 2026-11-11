"""Web API (G1 v1) of the technical-report template manager queries (AD01.01).

``/api/web/comedores/`` is published by the comedores backend (``url_prefixes``
in ``src/backends/config/backends.json``). In a split deploy the core checks the
session and the web prerequisites and signs each request; the runtime only
serves requests its ``WebGateMiddleware`` verified. In the monolith
``WebGatePermission`` evaluates the same policy locally. After that the native
guards apply unchanged: ``permissions_any_required`` with
``admisiones.gestionar_templates_informe_tecnico`` and the
``GestorTemplatesPermissionMixin`` test (superuser bypass included). There is no
per-object scope, as in the native views.

Each endpoint runs the native view itself (``setup()``, queryset, filters,
pagination and context), so it cannot drift from the HTML page; this module only
projects that context to JSON. Every page is read-only (GET). The actions of the
native pages (create, publish or discard a version, deactivate a template,
toggle a variable, manage an incident) keep posting to their native URLs, and
the DOCX preview stays the native GET of the version editor.
"""

from django.contrib import messages
from django.http import Http404
from django.template.defaultfilters import date as date_filter
from django.template.defaultfilters import title as title_filter
from django.template.defaultfilters import truncatechars, urlencode
from django.urls import reverse
from django.utils import timezone
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import NotFound
from rest_framework.permissions import BasePermission
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.views import APIView

# The exact predicate of ``permissions_any_required``, the native URL guard.
from core.decorators import _has_any_permissions
from core.pagination import build_compact_page_range
from core.web_gate import WebGatePermission
from admisiones.views.templates_informe_tecnico import (
    TEMPLATE_MANAGE_PERMISSION,
    IncidenciaTemplateInformeTecnicoDetailView,
    IncidenciaTemplateInformeTecnicoListView,
    PlantillaInformeTecnicoDetailView,
    PlantillaInformeTecnicoListView,
    VariableTemplateInformeTecnicoListView,
)
from iam.services import user_has_permission_code

MESSAGE_LEVELS = {
    messages.DEBUG: "info",
    messages.INFO: "info",
    messages.SUCCESS: "success",
    messages.WARNING: "warning",
    messages.ERROR: "error",
}
FILTROS = (
    "tipo_admision",
    "tipo_convenio",
    "es_ex_pnud",
    "estado_convenio_pnud",
    "tipo_renovacion",
    "estado_financiamiento",
    "informe_complementario_modifica_prestaciones",
)
OPCIONES = (
    "tipos_admision",
    "opciones_ex_pnud",
    "estados_convenio_pnud",
    "tipos_renovacion",
    "estados_financiamiento",
    "opciones_informe_complementario",
)


class GestorTemplates(BasePermission):
    """The native decorator and ``GestorTemplatesPermissionMixin``, in that order."""

    def has_permission(self, request, view):
        user = request.user
        return _has_any_permissions(
            user, [TEMPLATE_MANAGE_PERMISSION]
        ) and user_has_permission_code(user, TEMPLATE_MANAGE_PERMISSION)


class GestorTemplatesWebView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [WebGatePermission, GestorTemplates]
    renderer_classes = [JSONRenderer]
    http_method_names = ["get", "head"]


def pending_messages(request):
    """Consume queued Django messages exactly as the native page would."""
    return [
        {
            "message": str(message),
            "level": MESSAGE_LEVELS.get(message.level, "info"),
        }
        for message in messages.get_messages(request)
    ]


def _native(view_class, request, **kwargs):
    view = view_class()
    view.setup(request._request, **kwargs)  # pylint: disable=protected-access
    return view


def _list_context(view_class, request):
    vista = _native(view_class, request)
    try:
        vista.object_list = vista.get_queryset()
        return vista.get_context_data()
    except Http404 as exc:
        raise NotFound() from exc


def _detail_context(view_class, request, pk):
    vista = _native(view_class, request, pk=pk)
    try:
        vista.object = vista.get_object()
    except Http404 as exc:
        raise NotFound() from exc
    return vista.get_context_data(object=vista.object)


def _fecha(value):
    """``|date:"d/m/Y H:i"`` in the active time zone, as the template renders it."""
    return date_filter(timezone.localtime(value), "d/m/Y H:i") if value else None


def _choices(choices):
    return [
        {"value": str(valor), "label": str(etiqueta)} for valor, etiqueta in choices
    ]


def _query_without_page(request):
    """Prefix of the ``components/pagination.html`` links (``busqueda`` dropped)."""
    return "".join(
        f"{clave}={urlencode(valor)}&"
        for clave, valor in request.GET.items()
        if clave not in ("page", "busqueda")
    )


def _pagina(context, request):
    page = context["page_obj"]
    return {
        "is_paginated": context["is_paginated"],
        "number": page.number,
        "count": page.paginator.count,
        # ``{% if page_obj %}``: an empty page hides the count line.
        "has_rows": len(page.object_list) > 0,
        "previous": page.previous_page_number() if page.has_previous() else None,
        "next": page.next_page_number() if page.has_next() else None,
        "range": [
            "…" if numero in ("...", "…") else numero
            for numero in build_compact_page_range(page)
        ],
        "query_without_page": _query_without_page(request),
    }


def _navigation():
    return {
        "templates": reverse("gestor_templates_listar"),
        "variables": reverse("gestor_templates_variables_listar"),
        "incidencias": reverse("gestor_templates_incidencias_listar"),
    }


def _combinacion(plantilla):
    """The «Combinación» cell of ``list.html`` (whitespace as the browser shows it)."""
    partes = [plantilla.get_tipo_admision_display(), plantilla.tipo_convenio.nombre]
    if plantilla.tipo_admision == "incorporacion":
        partes.append(f"Ex PNUD: {plantilla.get_es_ex_pnud_display()}")
        if plantilla.es_ex_pnud == "si":
            partes.append(f"PNUD: {plantilla.get_estado_convenio_pnud_display()}")
    else:
        partes += [
            str(plantilla.get_tipo_renovacion_display()),
            str(plantilla.get_estado_financiamiento_display()),
            "Informe complementario: "
            f"{plantilla.get_informe_complementario_modifica_prestaciones_display()}",
        ]
    return " · ".join(str(parte) for parte in partes)


def _version_vigente(plantilla):
    publicacion = getattr(plantilla, "publicacion_vigente", None)
    return publicacion.version.numero if publicacion else None


class PlantillasListWebView(GestorTemplatesWebView):
    """``GET /api/web/comedores/admisiones/plantillas-informe/``: ``list.html``."""

    def get(self, request):
        context = _list_context(PlantillaInformeTecnicoListView, request)
        return Response(
            {
                "estado_filtro": context["estado_filtro"],
                "busqueda": context["busqueda"],
                "filtros": context["filtros"],
                "opciones": {
                    **{clave: _choices(context[clave]) for clave in OPCIONES},
                    "tipos_convenio": [
                        {"value": str(convenio.pk), "label": convenio.nombre}
                        for convenio in context["tipos_convenio"]
                    ],
                },
                "results": [
                    {
                        "id": plantilla.pk,
                        "codigo": plantilla.codigo,
                        "nombre": plantilla.nombre,
                        "descripcion": (
                            truncatechars(plantilla.descripcion, 85)
                            if plantilla.descripcion
                            else ""
                        ),
                        "combinacion": _combinacion(plantilla),
                        "version_vigente": _version_vigente(plantilla),
                        "estado": plantilla.estado,
                        "estado_display": plantilla.get_estado_display(),
                        "url": reverse("gestor_templates_detalle", args=[plantilla.pk]),
                    }
                    for plantilla in context["plantillas"]
                ],
                "page": _pagina(context, request),
                "urls": {**_navigation(), "crear": reverse("gestor_templates_crear")},
                "messages": pending_messages(request),
            }
        )


def _condiciones(plantilla):
    """The ``<dl>`` items of ``detail.html``."""
    items = [
        ("Tipo de admisión", plantilla.get_tipo_admision_display()),
        ("Tipo de convenio", plantilla.tipo_convenio.nombre),
    ]
    if plantilla.tipo_admision == "incorporacion":
        items.append(("Ex PNUD", plantilla.get_es_ex_pnud_display()))
        if plantilla.es_ex_pnud == "si":
            items.append(
                ("Convenio PNUD", plantilla.get_estado_convenio_pnud_display())
            )
    else:
        items += [
            ("Renovación", plantilla.get_tipo_renovacion_display()),
            (
                "Financiamiento",
                f"{plantilla.get_estado_financiamiento_display()} · "
                f"{plantilla.get_informe_complementario_modifica_prestaciones_display()}",
            ),
        ]
    return [{"term": term, "value": str(value)} for term, value in items]


class PlantillaDetailWebView(GestorTemplatesWebView):
    """``GET /api/web/comedores/admisiones/plantillas-informe/<pk>/``: ``detail.html``."""

    def get(self, request, pk):
        context = _detail_context(PlantillaInformeTecnicoDetailView, request, pk)
        plantilla = context["plantilla"]
        borrador = context["borrador_actual"]
        version_url = "gestor_templates_version_{}"
        return Response(
            {
                "id": plantilla.pk,
                "codigo": plantilla.codigo,
                "nombre": plantilla.nombre,
                "descripcion": plantilla.descripcion,
                "estado": plantilla.estado,
                "estado_display": plantilla.get_estado_display(),
                "condiciones": _condiciones(plantilla),
                "borrador": (
                    {
                        "id": borrador.pk,
                        "numero": borrador.numero,
                        "modificado": _fecha(borrador.modificado),
                        "urls": {
                            accion: reverse(
                                version_url.format(accion),
                                args=[plantilla.pk, borrador.pk],
                            )
                            for accion in ("editar", "publicar", "descartar")
                        },
                    }
                    if borrador
                    else None
                ),
                "historial": [
                    {
                        "id": version.pk,
                        "numero": version.numero,
                        "estado": version.estado,
                        "estado_display": version.get_estado_display(),
                        "creado": _fecha(version.creado),
                        "publicado": _fecha(version.publicado),
                    }
                    for version in context["versiones_historial"]
                ],
                "urls": {
                    **_navigation(),
                    "version_crear": reverse(
                        "gestor_templates_version_crear", args=[plantilla.pk]
                    ),
                    "inactivar": reverse(
                        "gestor_templates_inactivar", args=[plantilla.pk]
                    ),
                },
                "messages": pending_messages(request),
            }
        )


class VariablesListWebView(GestorTemplatesWebView):
    """``GET /api/web/comedores/admisiones/plantillas-informe/variables/``.

    ``variables_list.html`` shows the first page only (no paginator, native
    bug AD01-B2); ``?page=`` is still honoured and an invalid page is a 404.
    """

    def get(self, request):
        context = _list_context(VariableTemplateInformeTecnicoListView, request)
        return Response(
            {
                "estado_filtro": context["estado_filtro"],
                "busqueda": context["busqueda"],
                "results": [
                    {
                        "id": variable.pk,
                        "categoria": variable.categoria,
                        "nombre": variable.nombre,
                        "descripcion": variable.descripcion,
                        "token": variable.token,
                        "activo": variable.activo,
                        "alternar_url": reverse(
                            "gestor_templates_variables_alternar", args=[variable.pk]
                        ),
                    }
                    for variable in context["variables"]
                ],
                "urls": _navigation(),
                "messages": pending_messages(request),
            }
        )


class IncidenciasListWebView(GestorTemplatesWebView):
    """``GET /api/web/comedores/admisiones/plantillas-informe/incidencias/``."""

    def get(self, request):
        context = _list_context(IncidenciaTemplateInformeTecnicoListView, request)
        return Response(
            {
                "estado_filtro": context["estado_filtro"],
                "busqueda": context["busqueda"],
                "estados": _choices(context["estados"]),
                "results": [
                    {
                        "id": incidencia.pk,
                        "codigo": incidencia.codigo,
                        "clave_condiciones": incidencia.clave_condiciones,
                        "cantidad_casos": incidencia.cantidad_casos,
                        "ultima_fecha": _fecha(incidencia.ultima_fecha),
                        "estado": incidencia.estado,
                        "estado_display": incidencia.get_estado_display(),
                        "url": reverse(
                            "gestor_templates_incidencia_detalle", args=[incidencia.pk]
                        ),
                    }
                    for incidencia in context["incidencias"]
                ],
                "page": _pagina(context, request),
                "urls": _navigation(),
                "messages": pending_messages(request),
            }
        )


def _default(value):
    """``|default:"-"``."""
    return str(value) if value else "-"


def _descripcion(condicion):
    descripcion = condicion.get("descripcion") if isinstance(condicion, dict) else None
    return _default(descripcion)


def _form_field(form, name):
    bound = form[name]
    field = form.fields[name]
    payload = {
        "name": name,
        "label": str(bound.label),
        "required": field.required,
        "value": "" if bound.value() is None else str(bound.value()),
    }
    if name != "observaciones":
        payload["choices"] = [
            {"value": "" if valor is None else str(valor), "label": str(etiqueta)}
            for valor, etiqueta in field.choices
        ]
    return payload


class IncidenciaDetailWebView(GestorTemplatesWebView):
    """``GET /api/web/comedores/admisiones/plantillas-informe/incidencias/<pk>/``.

    The management form is the unbound native form; saving it keeps posting to
    the native URL (AD01.02).
    """

    def get(self, request, pk):
        context = _detail_context(
            IncidenciaTemplateInformeTecnicoDetailView, request, pk
        )
        incidencia = context["incidencia"]
        form = context["form"]
        anterior = incidencia.incidencia_anterior
        return Response(
            {
                "id": incidencia.pk,
                "codigo": incidencia.codigo,
                "cantidad_casos": incidencia.cantidad_casos,
                "primera_fecha": _fecha(incidencia.primera_fecha),
                "ultima_fecha": _fecha(incidencia.ultima_fecha),
                "incidencia_anterior": anterior.codigo if anterior else None,
                "clave_condiciones": incidencia.clave_condiciones,
                "condiciones": [
                    {"clave": title_filter(clave), "descripcion": _descripcion(valor)}
                    for clave, valor in (incidencia.condiciones or {}).items()
                ],
                "form": [
                    _form_field(form, name)
                    for name in ("estado", "plantilla", "observaciones")
                ],
                "casos": [
                    {
                        "id": caso.pk,
                        "admision": str(caso.admision_id_reportada),
                        "informe": _default(caso.informe_id_reportado),
                        "comedor": _default(caso.comedor_nombre),
                        "organizacion": _default(caso.organizacion_nombre),
                        "reportado_por": _default(caso.reportado_por),
                        "creado": _fecha(caso.creado),
                    }
                    for caso in incidencia.casos.all()
                ],
                "urls": {
                    **_navigation(),
                    "gestionar": reverse(
                        "gestor_templates_incidencia_detalle", args=[incidencia.pk]
                    ),
                },
                "messages": pending_messages(request),
            }
        )
