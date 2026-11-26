"""Web API (G1 v1) of the CDF preinscription, beneficiaries and responsables (CDF03).

Same access chain as ``centrodefamilia.web_api``: G1 session and web
prerequisites, then ``centrodefamilia.view_centro``. Beneficiaries and
responsables have no centre or territorial scope today (D1 keeps it): every
holder of ``view_centro`` sees the full roll.

- CDF03.02 (preinscription): the CUIL and responsable searches run the native
  service functions (RENAPER lookup and ``renaper_cache`` in the session
  included) and answer their JSON as is. The POST runs
  ``procesar_preinscripcion``, shared with the native view, but never
  ``generar_respuesta``: no Django message is queued for a later page.
- CDF03.01 (consultation): lists and details run the native views (filters,
  exact or NoCount pagination, the 404 rules) and project their context. The
  only addition is ``beneficiarios/exportar/disponible/``: the native CSV
  answers "no rows" with a Django message that a React page never receives.

Responses are ``private, no-store`` and are never logged.
"""

import json
from html.parser import HTMLParser
from urllib.parse import quote

from crispy_forms.templatetags.crispy_forms_filters import as_crispy_field
from django.http import Http404
from django.template.defaultfilters import date as date_filter
from django.urls import reverse
from rest_framework.exceptions import NotFound
from rest_framework.response import Response

from centrodefamilia.forms import BeneficiarioForm, ResponsableForm
from centrodefamilia.models import BeneficiarioResponsable
from centrodefamilia.services.beneficiarios_service.impl import (
    buscar_cuil_beneficiario,
    buscar_responsable_renaper,
    errores_preinscripcion,
    get_filtered_beneficiarios,
    procesar_preinscripcion,
)
from centrodefamilia.views.beneficiarios import (
    BeneficiariosDetailView,
    BeneficiariosListView,
    ResponsableDetailView,
    ResponsableListView,
)
from centrodefamilia.views.beneficiarios_export import BeneficiariosExportView
from centrodefamilia.web_api import (
    CdfWebView,
    _fecha,
    native_view,
    pending_messages,
)
from core.pagination import build_compact_page_range
from core.templatetags.custom_filters import has_any_perm, safe_getattr

SUCCESS = {
    "status": "success",
    "message": "Preinscripción confirmada exitosamente",
    "toast": "Datos cargados con éxito",
}
NO_ROWS = "No hay beneficiarios para exportar con el filtro aplicado."

# Fields and columns of ``beneficiarios_form.html`` (only what the page renders).
BENEFICIARIO_LAYOUT = (
    ("nombre", "col-md-6"),
    ("apellido", "col-md-6"),
    ("dni", "col-md-6"),
    ("cuil", "col-md-6"),
    ("genero", "col-md-6"),
    ("fecha_nacimiento", "col-md-6"),
    ("domicilio", "col-md-12"),
    ("provincia", "col-md-4"),
    ("municipio", "col-md-4"),
    ("localidad", "col-md-4"),
    ("calle", "col-md-4"),
    ("altura", "col-md-2"),
    ("piso_vivienda", "col-md-2"),
    ("departamento_vivienda", "col-md-2"),
    ("codigo_postal", "col-md-2"),
    ("barrio", "col-md-6"),
    ("monoblock", "col-md-6"),
    ("prefijo_celular", "col-md-2"),
    ("numero_celular", "col-md-4"),
    ("prefijo_telefono_fijo", "col-md-2"),
    ("numero_telefono_fijo", "col-md-4"),
    ("correo_electronico", "col-12"),
    ("estado_academico", "col-md-2"),
    ("nivel_educativo_actual", "col-md-5"),
    ("maximo_nivel_educativo", "col-md-5"),
    ("institucion_academica", "col-md-12"),
    ("actividad_preferida", "col-6"),
    ("actividades_extracurriculares", "col-3"),
    ("actividades_detalle", "col-3"),
)
RESPONSABLE_LAYOUT = (
    ("nombre", "col-md-6"),
    ("apellido", "col-md-6"),
    ("dni", "col-md-6"),
    ("cuil", "col-md-6"),
    ("genero", "col-md-4"),
    ("fecha_nacimiento", "col-md-4"),
    ("vinculo_parental", "col-md-4"),
    ("calle", "col-md-4"),
    ("altura", "col-md-2"),
    ("piso_vivienda", "col-md-2"),
    ("departamento_vivienda", "col-md-2"),
    ("codigo_postal", "col-md-2"),
    ("barrio", "col-md-6"),
    ("monoblock", "col-md-6"),
    ("provincia", "col-md-4"),
    ("municipio", "col-md-4"),
    ("localidad", "col-md-4"),
    ("prefijo_celular", "col-md-2"),
    ("numero_celular", "col-md-4"),
    ("prefijo_telefono_fijo", "col-md-2"),
    ("numero_telefono_fijo", "col-md-4"),
    ("correo_electronico", "col-md-12"),
)


def _json(native_response):
    """A native ``JsonResponse`` answered with the same status and body."""
    return Response(
        json.loads(native_response.content), status=native_response.status_code
    )


def _django(request):
    return request._request  # pylint: disable=protected-access


# --- CDF03.02 preinscription --------------------------------------------------


class _ControlAttrs(HTMLParser):
    """Attributes of the controls crispy renders for one field (``id_<name>...``)."""

    def __init__(self, control_id):
        super().__init__()
        self.control_id = control_id
        self.controls = []

    def handle_starttag(self, tag, attrs):
        values = {key: "" if value is None else value for key, value in attrs}
        if tag in ("input", "select", "textarea") and values.get("id", "").startswith(
            self.control_id
        ):
            values.pop("id")
            values.pop("name", None)
            self.controls.append({"tag": tag, "attrs": values})


def _kind(field, controls):
    first = controls[0]
    if first["tag"] == "select":
        return "selectmultiple" if "multiple" in first["attrs"] else "select"
    if first["attrs"].get("type") == "checkbox":
        multiple = len(controls) > 1 or field.name == "actividades_detalle"
        return "checkboxmultiple" if multiple else "checkbox"
    return "input"


def _form_field(form, name, column):
    bound = form[name]
    parser = _ControlAttrs(bound.auto_id)
    parser.feed(str(as_crispy_field(bound)))
    controls = parser.controls
    kind = _kind(bound, controls) if controls else "checkboxmultiple"
    payload = {
        "name": name,
        "label": str(bound.label),
        "required": bound.field.required,
        "kind": kind,
        "column": column,
        "attrs": (
            controls[0]["attrs"] if controls and kind != "checkboxmultiple" else {}
        ),
    }
    if kind in ("select", "selectmultiple", "checkboxmultiple"):
        payload["choices"] = [
            {"value": str(getattr(value, "value", value)), "label": str(label)}
            for value, label in bound.field.choices
        ]
    return payload


def _form_fields(form, layout):
    return [_form_field(form, name, column) for name, column in layout]


def _form_errors(errors):
    return {
        name: [str(message) for message in messages]
        for name, messages in errors.items()
    }


class PreinscripcionOptionsWebView(CdfWebView):
    """``GET .../beneficiarios/preinscripcion/options/``: both unbound forms."""

    def get(self, request):
        return Response(
            {
                "beneficiario": _form_fields(BeneficiarioForm(), BENEFICIARIO_LAYOUT),
                "responsable": _form_fields(ResponsableForm(), RESPONSABLE_LAYOUT),
                "urls": {
                    "municipios": reverse("ajax_load_municipios"),
                    "localidades": reverse("ajax_load_localidades"),
                },
                "messages": pending_messages(request),
            }
        )


class BuscarCuilWebView(CdfWebView):
    """``GET .../beneficiarios/buscar-cuil/?cuil=``: ``buscar_cuil_beneficiario``."""

    def get(self, request):
        return _json(
            buscar_cuil_beneficiario(_django(request), request.GET.get("cuil"))
        )


class BuscarResponsableWebView(CdfWebView):
    """``GET .../beneficiarios/buscar-responsable/?dni=&sexo=``: the native search."""

    def get(self, request):
        return _json(
            buscar_responsable_renaper(
                _django(request), request.GET.get("dni"), request.GET.get("sexo")
            )
        )


class PreinscripcionWebView(CdfWebView):
    """``POST .../beneficiarios/preinscripcion/``: ``procesar_preinscripcion``."""

    http_method_names = ["post"]

    def post(self, request):
        try:
            beneficiario, forms_data = procesar_preinscripcion(_django(request))
        except Exception as exc:  # pylint: disable=broad-exception-caught
            # Parity with ``manejar_request_beneficiarios`` (text of the error).
            return Response(
                {"status": "error", "message": f"Error al guardar: {exc}"}, status=500
            )
        if beneficiario:
            return Response(SUCCESS)
        errores = errores_preinscripcion(forms_data)
        return Response(
            {
                "status": "error",
                "errors": {
                    tipo: _form_errors(lista) for tipo, lista in errores.items()
                },
            },
            status=400,
        )


# --- CDF03.01 consultation ----------------------------------------------------


def _query_without_page(request):
    """Prefix of ``components/pagination.html`` links (``page`` and ``busqueda`` dropped)."""
    return "".join(
        f"{clave}={quote(valor, safe='/')}&"
        for clave, valor in request.GET.items()
        if clave not in ("page", "busqueda")
    )


def _breadcrumb(items):
    ultimo = len(items) - 1
    return [
        {
            "text": str(item["text"]),
            "url": (
                item["url"]
                if item.get("url") and not item.get("active") and indice != ultimo
                else None
            ),
        }
        for indice, item in enumerate(items)
    ]


def _cell(item, name):
    """``{{ item|getattr:field.name }}`` of ``data_table.html`` (``None`` is "-")."""
    return str(safe_getattr(item, name))


def _lista(request, context, items, detail_name):
    fields = context["table_fields"]
    page = context["page_obj"]
    exact = getattr(page.paginator, "count", None) is not None
    return {
        "breadcrumb": _breadcrumb(context["breadcrumb_items"]),
        "filters_config": context["filters_config"],
        "favorites": {
            "section": context["seccion_filtros_favoritos"],
            "url": reverse("filtros_favoritos"),
            "detail_url_template": reverse("detalle_filtro_favorito", kwargs={"pk": 0}),
        },
        "columns": context["column_config"],
        "headers": [
            {
                "title": str(header["title"]),
                "width": header.get("width") or "",
                "sortable": bool(header.get("sortable")),
                "sort_key": header.get("sort_key") or header["title"],
            }
            for header in context["table_headers"]
        ],
        "results": [
            {
                "id": item.pk,
                "cells": [_cell(item, field["name"]) for field in fields],
                "url": reverse(detail_name, args=[item.pk]),
            }
            for item in items
        ],
        "count": page.paginator.count if exact else None,
        "page": page.number,
        "page_size": page.paginator.per_page,
        "pages": page.paginator.num_pages if exact else None,
        "has_next": page.has_next(),
        "has_previous": page.has_previous(),
        "page_range": [
            "..." if numero in ("...", "…") else numero
            for numero in (
                build_compact_page_range(page)
                if exact
                else context.get("page_range") or []
            )
        ],
        "is_paginated": context["is_paginated"],
        "query_without_page": _query_without_page(request),
        "filters": {"filters": request.GET.get("filters", "")},
        "messages": pending_messages(request),
    }


def _native_list(view_class, request):
    vista = native_view(view_class, request)
    try:
        vista.object_list = vista.get_queryset()
        return vista.get_context_data()
    except Http404 as exc:
        raise NotFound() from exc


def can_export(user):
    """``search_bar.html``: superuser or ``has_any_perm`` with ``export_permissions``."""
    codes = ",".join(BeneficiariosExportView.export_permission_codes)
    return bool(user.is_superuser or has_any_perm(user, codes))


class BeneficiariosListWebView(CdfWebView):
    """``GET /api/web/cdf/beneficiarios/``: ``BeneficiariosListView`` (exact pages of 10)."""

    def get(self, request):
        context = _native_list(BeneficiariosListView, request)
        payload = _lista(
            request, context, context["beneficiarios"], "beneficiarios_detail"
        )
        payload["can_export"] = can_export(request.user)
        payload["urls"] = {
            "list": context["filters_action"],
            "reset": context["reset_url"],
            "add": context["add_url"],
            "export": reverse("beneficiarios_export"),
            "export_available": reverse("web_cdf_beneficiarios_exportar_disponible"),
        }
        return Response(payload)


class BeneficiariosExportDisponibleWebView(CdfWebView):
    """``GET .../beneficiarios/exportar/disponible/``: whether the native CSV has rows."""

    def get(self, request):
        BeneficiariosExportView().check_export_permission(_django(request))
        existe = get_filtered_beneficiarios(_django(request)).exists()
        return Response({"exists": existe, "message": "" if existe else NO_ROWS})


class ResponsablesListWebView(CdfWebView):
    """``GET /api/web/cdf/responsables/``: ``ResponsableListView`` (NoCount of 10)."""

    def get(self, request):
        context = _native_list(ResponsableListView, request)
        payload = _lista(
            request, context, context["responsables"], "responsables_detail"
        )
        payload["urls"] = {
            "list": context["filters_action"],
            "reset": context["reset_url"],
        }
        return Response(payload)


def _texto(value, vacio=None):
    """``{{ value }}`` (``None`` included) or ``{{ value|default:vacio }}``."""
    if vacio is not None and not value:
        return vacio
    return "None" if value is None else str(value)


def _dia(value):
    return date_filter(value, "d/m/Y") if value else ""


def _telefono(prefijo, numero):
    return f"{prefijo}-{numero}" if prefijo and numero else "No especificado"


def _calle(persona):
    return f"{_texto(persona.calle)} {persona.altura or ''}"


def _native_object(view_class, request, pk):
    vista = native_view(view_class, request, pk=pk)
    try:
        return vista.get_object(), vista
    except Http404 as exc:
        raise NotFound() from exc


class BeneficiarioDetailWebView(CdfWebView):
    """``GET /api/web/cdf/beneficiarios/<pk>/``: ``beneficiarios_detail.html``."""

    def get(self, request, pk):
        beneficiario, _ = _native_object(BeneficiariosDetailView, request, pk)
        responsable = beneficiario.responsable
        detalle = [a.nombre for a in beneficiario.actividades_detalle.all()]
        return Response(
            {
                "id": beneficiario.pk,
                "nombre_completo": f"{beneficiario.apellido}, {beneficiario.nombre}",
                "dni": str(beneficiario.dni),
                "cuil": str(beneficiario.cuil),
                "genero_display": str(beneficiario.get_genero_display()),
                "fecha_nacimiento": _dia(beneficiario.fecha_nacimiento),
                "correo_electronico": _texto(
                    beneficiario.correo_electronico, "No especificado"
                ),
                "fecha_creado": _fecha(beneficiario.fecha_creado),
                "responsable": {
                    "nombre_completo": f"{responsable.apellido}, {responsable.nombre}",
                    "dni": str(responsable.dni),
                    "cuil": str(responsable.cuil),
                    "vinculo_display": str(responsable.get_vinculo_parental_display()),
                    "celular": _telefono(
                        responsable.prefijo_celular, responsable.numero_celular
                    ),
                    "url": reverse("responsables_detail", args=[responsable.pk]),
                },
                "domicilio": {
                    "domicilio": _texto(beneficiario.domicilio),
                    "calle": _calle(beneficiario),
                    "provincia": _texto(beneficiario.provincia),
                    "municipio": _texto(beneficiario.municipio),
                    "localidad": _texto(beneficiario.localidad),
                    "codigo_postal": _texto(
                        beneficiario.codigo_postal, "No especificado"
                    ),
                    "barrio": _texto(beneficiario.barrio, "No especificado"),
                },
                "academico": {
                    "estudia": bool(beneficiario.estado_academico),
                    "nivel_actual": (
                        str(beneficiario.get_nivel_educativo_actual_display())
                        if beneficiario.nivel_educativo_actual
                        else None
                    ),
                    "maximo_nivel": str(
                        beneficiario.get_maximo_nivel_educativo_display()
                    ),
                    "institucion": _texto(
                        beneficiario.institucion_academica, "No especificada"
                    ),
                },
                "actividad_preferida": [
                    str(a) for a in (beneficiario.actividad_preferida or [])
                ],
                "actividades_extracurriculares": bool(
                    beneficiario.actividades_extracurriculares
                ),
                "actividades_detalle": detalle,
                "messages": pending_messages(request),
            }
        )


class ResponsableDetailWebView(CdfWebView):
    """``GET /api/web/cdf/responsables/<pk>/``: ``responsable_detail.html``."""

    def get(self, request, pk):
        responsable, _ = _native_object(ResponsableDetailView, request, pk)
        vinculos = BeneficiarioResponsable.objects.filter(
            responsable=responsable
        ).select_related("beneficiario")
        return Response(
            {
                "id": responsable.pk,
                "nombre_completo": f"{responsable.apellido}, {responsable.nombre}",
                "dni": str(responsable.dni),
                "cuil": str(responsable.cuil),
                "genero_display": str(responsable.get_genero_display()),
                "fecha_nacimiento": _dia(responsable.fecha_nacimiento),
                "celular": _telefono(
                    responsable.prefijo_celular, responsable.numero_celular
                ),
                "telefono_fijo": _telefono(
                    responsable.prefijo_telefono_fijo, responsable.numero_telefono_fijo
                ),
                "correo_electronico": _texto(
                    responsable.correo_electronico, "No especificado"
                ),
                "domicilio": {
                    "calle": _calle(responsable),
                    "piso_vivienda": _texto(
                        responsable.piso_vivienda, "No especificado"
                    ),
                    "departamento_vivienda": _texto(
                        responsable.departamento_vivienda, "No especificado"
                    ),
                    "barrio": _texto(responsable.barrio, "No especificado"),
                    "provincia": _texto(responsable.provincia),
                    "municipio": _texto(responsable.municipio),
                    "localidad": _texto(responsable.localidad),
                    "codigo_postal": _texto(
                        responsable.codigo_postal, "No especificado"
                    ),
                    "monoblock": _texto(responsable.monoblock, "No especificado"),
                },
                "vinculos": [
                    {
                        "beneficiario_id": v.beneficiario.pk,
                        "cuil": str(v.beneficiario.cuil),
                        "apellido_nombre": f"{v.beneficiario.apellido}, {v.beneficiario.nombre}",
                        "dni": str(v.beneficiario.dni),
                        "genero_display": str(v.beneficiario.get_genero_display()),
                        "fecha_nacimiento": _dia(v.beneficiario.fecha_nacimiento),
                        "vinculo_display": str(v.get_vinculo_parental_display()),
                        "fecha_creado": _fecha(v.fecha_creado),
                        "url": reverse(
                            "beneficiarios_detail", args=[v.beneficiario.pk]
                        ),
                    }
                    for v in vinculos
                ],
                "messages": pending_messages(request),
            }
        )
