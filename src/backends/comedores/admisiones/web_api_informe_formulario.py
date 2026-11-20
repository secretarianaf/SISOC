"""Web API (G1 v1) of the technical-report form schema (AD02.01, second delivery).

``GET /api/web/comedores/admisiones/informes/<tipo>/admision/<admision_id>/formulario/``
(create) and ``GET /api/web/comedores/admisiones/informes/<tipo>/<pk>/formulario/``
(edit) run the native ``InformeTecnicosCreateView`` / ``InformeTecnicosUpdateView``
(``get_form_class``, ``get_form_kwargs``, ``get_context_data``) and project the
*effective* form: only the fields that survive the native ``Form`` configuration
(exclusions, conditional fields, renewal antecedents), with the presence,
requiredness, initial value, choices and help text it computed. No model schema
and no client-defined fields are involved, and reading a field grants no write.

The access is the native URL guard (``comedores.view_comedor``,
``admisiones.view_admision`` or ``acompanamientos.view_informacionrelevante``,
superuser included), with no scope per admission. Saving (draft and submit),
DOCX generation and every other action stay on the native POST.
"""

from django import forms
from django.contrib import messages
from django.http import Http404
from django.urls import reverse
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import NotFound, ParseError
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.views import APIView

from core.web_gate import WebGatePermission
from admisiones.services.informes_service.impl import InformeService
from admisiones.views.web_views import (
    InformeTecnicosCreateView,
    InformeTecnicosUpdateView,
)
from admisiones.web_api_informes import VerInforme
from admisiones.web_api_templates import MESSAGE_LEVELS, _native

NOT_AVAILABLE = "El tipo de informe seleccionado no está disponible para carga online."


def _kind(widget):
    if isinstance(widget, forms.CheckboxInput):
        return "checkbox"
    if isinstance(widget, forms.Select):
        return "select"
    if isinstance(widget, forms.Textarea):
        return "textarea"
    if isinstance(widget, forms.DateInput):
        return "date"
    if isinstance(widget, forms.NumberInput):
        return "number"
    return "text"


def _attrs(bound, field):
    """The HTML attributes the native widget renders (class, data-*, limits...)."""
    attrs = {**field.widget.attrs, **(field.widget_attrs(field.widget) or {})}
    if field.required and field.widget.use_required_attribute(bound.initial):
        attrs["required"] = True
    return {str(k): v if isinstance(v, bool) else str(v) for k, v in attrs.items()}


def _field(form, name):
    bound, field = form[name], form.fields[name]
    kind = _kind(field.widget)
    value = bound.value()
    if kind == "checkbox":
        value = bool(value)
    elif kind != "select":
        value = field.widget.format_value(value)
    payload = {
        "name": name,
        "label": str(bound.label) if bound.label else "",
        "kind": kind,
        "required": field.required,
        "value": value if kind == "checkbox" else "" if value is None else str(value),
        "help_text": str(field.help_text or ""),
        "max_length": getattr(field, "max_length", None),
        "errors": list(bound.errors),
        "id": bound.id_for_label,
        "attrs": _attrs(bound, field),
        "widget": type(field.widget).__name__,
    }
    if kind == "select":
        payload["choices"] = [
            {"value": "" if v is None else str(v), "label": str(label)}
            for v, label in field.choices
        ]
    return payload


def _antecedentes(form):
    return [
        {
            "admision_id": item["admision"].pk,
            "incluida": item["incluida"].name,
            "resolucion": item["resolucion"].name,
            "convenio": item["convenio"].name,
            "expediente": item["expediente"].name,
        }
        for item in getattr(form, "antecedentes_renovaciones_campos", [])
    ]


def _publicacion(context):
    publicacion = context.get("template_publicacion")
    return {
        "plantilla": (
            {
                "codigo": publicacion.plantilla.codigo,
                "nombre": publicacion.plantilla.nombre,
                "version": publicacion.version.numero,
            }
            if publicacion
            else None
        ),
        "error": context.get("template_error") or None,
        "configuracion_faltante": bool(context.get("template_configuracion_faltante")),
        "detalle_copiable": context.get("template_detalle_copiable") or "",
    }


def prepare_native_view(request, tipo, admision_id=None, pk=None):
    """The native create or update view, set up as its ``dispatch`` would leave it."""
    if admision_id is not None:
        vista = _native(
            InformeTecnicosCreateView, request, tipo=tipo, admision_id=admision_id
        )
        vista.object = None
        vista.admision_obj, vista.tipo = InformeService.get_admision_y_tipo_from_kwargs(
            vista.kwargs
        )
        if not vista.admision_obj:
            raise NotFound()
        tipo_informe = vista.tipo
    else:
        vista = _native(InformeTecnicosUpdateView, request, tipo=tipo, pk=pk)
        try:
            vista.object = vista.get_object()
        except Http404 as exc:
            raise NotFound() from exc
        tipo_informe = vista.object.tipo
    if tipo_informe not in vista.tipos_permitidos:
        raise ParseError(NOT_AVAILABLE)
    return vista


def fields_payload(form):
    """The effective fields of a (bound or unbound) native form."""
    return [_field(form, name) for name in form.fields]


def _messages(request):
    """Queued messages with their tags: the page draws ``configuracion-template`` in the form."""
    return [
        {
            "message": str(message),
            "level": MESSAGE_LEVELS.get(message.level, "info"),
            "tags": message.tags,
        }
        for message in messages.get_messages(request)
    ]


def _urls(context, informe):
    admision = context["admision"]
    previsualizar = (
        reverse(
            "informe_tecnico_previsualizar_template", args=[informe.tipo, informe.pk]
        )
        if informe and informe.estado_formulario != "finalizado"
        else None
    )
    return {
        "volver": reverse("admisiones_tecnicos_editar", args=[admision.pk]),
        "previsualizar": previsualizar,
        "reportar_faltante": reverse(
            "admisiones_reportar_configuracion_faltante_template", args=[admision.pk]
        ),
        "localidades": reverse("ajax_load_localidades"),
    }


class InformeFormularioWebView(APIView):
    """Effective form of the create and edit pages."""

    authentication_classes = [SessionAuthentication]
    permission_classes = [WebGatePermission, VerInforme]
    renderer_classes = [JSONRenderer]
    http_method_names = ["get", "head"]

    def get(self, request, tipo, admision_id=None, pk=None):
        vista = prepare_native_view(request, tipo, admision_id, pk)
        form = vista.get_form()
        context = vista.get_context_data(form=form)
        informe = vista.object
        return Response(
            {
                "tipo": tipo,
                "admision_id": context["admision"].pk,
                "informe_id": informe.pk if informe else None,
                "estado": informe.estado if informe else "",
                "comedor": context["admision"].comedor.nombre,
                "permite_no_corresponde": form.permite_no_corresponde_fecha_vencimiento,
                "require_full": form.require_full,
                "fields": fields_payload(form),
                "antecedentes": _antecedentes(form),
                "non_field_errors": list(form.non_field_errors()),
                "campos_a_subsanar": context.get("campos_a_subsanar", []),
                "observacion": (
                    context["observacion"].texto if context.get("observacion") else ""
                ),
                "publicacion": _publicacion(context),
                "estado_formulario": informe.estado_formulario if informe else "",
                "urls": _urls(context, informe),
                "messages": _messages(request),
            }
        )
