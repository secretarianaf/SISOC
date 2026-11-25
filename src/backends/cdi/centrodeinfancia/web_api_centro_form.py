"""Web API (G1 v1) of the CDI centre create and edit screens for React.

Session transport over the native views: each API view inherits
``CentroDeInfanciaCreateView`` / ``CentroDeInfanciaUpdateView``, so the scoped
centre (404 outside the actor's scope), ``CentroDeInfanciaForm`` with its
required, locked and conditional fields, the signed 15-minute RENAPER token of
the referente block, the save, the referente provisioning, the success message
and the CDI-A3 read-only veto for SIMEPI auditors stay the native ones. Order of
checks:

1. G1 (``WebGatePermission``): 401/403 JSON, or the signed attestation.
2. The same permission code as the URL decorator in ``centrodeinfancia/urls.py``
   (``add_centrodeinfancia`` and ``change_centrodeinfancia``).
3. The native dispatch.

The API sends the fields ``centrodeinfancia_form.html`` draws (``CAMPOS``), each
with the data its crispy markup needs (label, widget, value, choices, errors);
the check-box groups as options; the opening hours per day; and the RENAPER
block. A native redirect becomes ``{"ok": true, "redirect": <Location>}`` and
the queued messages show on the destination like the HTML. A POST that is
answered with the form again (an invalid form) returns 400 with the same
payload. Responses are ``private, no-store``.
"""

from django.forms import CheckboxInput, Textarea
from django.http import JsonResponse
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie

from centrodeinfancia.forms import CentroDeInfanciaForm
from centrodeinfancia.services_renaper_bloques import BLOQUE_REFERENTE
from centrodeinfancia.views import (
    CentroDeInfanciaCreateView,
    CentroDeInfanciaUpdateView,
)
from centrodeinfancia.web_api import pending_messages
from centrodeinfancia.web_api_formularios import (
    TransporteFormularioMixin,
    bloque_renaper_web,
    campo_web,
    privada,
)

PERMISO_ALTA = "centrodeinfancia.add_centrodeinfancia"
PERMISO_EDICION = "centrodeinfancia.change_centrodeinfancia"
MULTIPLES = ("meses_funcionamiento", "dias_funcionamiento", "oferta_servicios")
_ANTES_DE_HORARIOS = (
    "nombre",
    "organizacion",
    "cuit_organizacion_gestiona",
    "ambito",
    "telefono",
    "mail",
    "fecha_inicio",
    "modalidad_gestion",
    "modalidad_gestion_otra",
    "provincia",
    "departamento",
    "decil_ipi",
    "municipio",
    "localidad",
    "codigo_postal",
    "calle",
    "numero",
    "latitud",
    "longitud",
)
_HORARIOS = tuple(
    f"horario_{dia}_{momento}"
    for dia, _etiqueta in CentroDeInfanciaForm.DIAS_SEMANA
    for momento in ("apertura", "cierre")
)
_DESPUES_DE_HORARIOS = (
    "tipo_jornada",
    "tipo_jornada_otra",
    "dni_referente",
    "nombre_referente",
    "apellido_referente",
    "cuil_referente",
    "email_referente",
    "telefono_referente",
)
# The fields ``centrodeinfancia_form.html`` draws, in template order. Nothing else is
# sent, so the page posts exactly what the native form posts.
CAMPOS = _ANTES_DE_HORARIOS + _HORARIOS + _DESPUES_DE_HORARIOS


def _valor_seleccionado(bound):
    """The option the native ``<select>`` marks as selected (``""`` when none)."""
    contexto = bound.field.widget.get_context(bound.html_name, bound.value(), {})
    for _nombre, opciones, _indice in contexto["widget"]["optgroups"]:
        for opcion in opciones:
            if opcion["selected"]:
                return str(opcion["value"])
    return ""


def _campo(form, nombre):
    """``campo_web`` plus what the centre page needs to draw the control."""
    bound = form[nombre]
    widget = bound.field.widget
    datos = campo_web(form, nombre)
    if isinstance(widget, Textarea):
        datos["widget"] = "textarea"
    if isinstance(widget, CheckboxInput):
        datos["widget"] = "checkbox"
        datos["checked"] = bool(bound.value())
        datos["value"] = ""
    elif datos["widget"] == "select":
        datos["value"] = _valor_seleccionado(bound)
    else:
        valor = widget.format_value(bound.value())
        datos["value"] = "" if valor is None else str(valor)
    return datos


def _multiple(campo):
    return {
        "label": str(campo.label),
        "required": bool(campo.field.required),
        "errors": [str(error) for error in campo.errors],
        "options": [
            {
                "id": opcion.id_for_label,
                "value": str(opcion.data["value"]),
                "label": str(opcion.choice_label),
                "checked": bool(opcion.data["selected"]),
            }
            for opcion in campo
        ],
    }


class _CentroTransportMixin(TransporteFormularioMixin):
    """The form payload of the native context; a rejected POST is a 400."""

    def render_to_response(self, context, **response_kwargs):
        form = context["form"]
        es_edicion = bool(form.instance.pk)
        cuerpo = {
            "is_edit": es_edicion,
            "non_field_errors": [str(error) for error in form.non_field_errors()],
            "fields": [_campo(form, nombre) for nombre in CAMPOS],
            "multiples": {nombre: _multiple(form[nombre]) for nombre in MULTIPLES},
            "dias": [
                {"dia": dia, "etiqueta": str(etiqueta)}
                for dia, etiqueta in form.DIAS_SEMANA
            ],
            "renaper": bloque_renaper_web(
                form,
                BLOQUE_REFERENTE,
                (context.get("renaper_tokens") or {}).get(BLOQUE_REFERENTE, ""),
                permite_cambiar=True,
            ),
            "urls": {
                "cancelar": (
                    reverse("centrodeinfancia_detalle", args=[form.instance.pk])
                    if es_edicion
                    else reverse("centrodeinfancia")
                ),
                "departamentos": reverse(
                    "centrodeinfancia_ajax_load_departamentos_ipi"
                ),
                "municipios": reverse("ajax_load_municipios"),
                "localidades": reverse("ajax_load_localidades"),
                "address_preview": reverse("address_preview"),
            },
            "messages": pending_messages(self.request),
        }
        # Every answer to a POST that is not a redirect is the form again: a rejection.
        estado = 400 if self.request.method == "POST" else 200
        return privada(JsonResponse(cuerpo, status=estado))


@method_decorator(ensure_csrf_cookie, name="dispatch")
@method_decorator(csrf_protect, name="dispatch")
class CentroCrearWebView(_CentroTransportMixin, CentroDeInfanciaCreateView):
    """``/api/web/cdi/centros/crear/``: native create."""

    permission_codes = (PERMISO_ALTA,)


@method_decorator(ensure_csrf_cookie, name="dispatch")
@method_decorator(csrf_protect, name="dispatch")
class CentroEditarWebView(_CentroTransportMixin, CentroDeInfanciaUpdateView):
    """``/api/web/cdi/centros/<pk>/editar/``: native edit."""

    permission_codes = (PERMISO_EDICION,)
