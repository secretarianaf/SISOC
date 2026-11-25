"""Web API (G1 v1) of the CDI worker create and edit screens (CDI05) for React.

Session transport over the native views: each API view inherits
``TrabajadorCentroInfanciaCreateView`` / ``TrabajadorCentroInfanciaUpdateView``,
so the scoped centre or worker (404 outside the actor's scope), the DNI search
(local citizens first, RENAPER only as the native view does it), the signed
15-minute RENAPER prefill token, ``TrabajadorCDIForm`` with its required, locked
and conditional fields, the save, the user provisioning and the success
messages stay the native ones. Order of checks:

1. G1 (``WebGatePermission``): 401/403 JSON, or the signed attestation in the
   runtime.
2. The same permission code as the URL decorator in ``centrodeinfancia/urls.py``
   (``add_trabajador`` and ``change_trabajador``; superuser bypass included).
3. The native dispatch, including the CDI-A3 read-only veto for SIMEPI
   auditors on every non-GET (``_AuditoriaSoloLecturaMixin``).

The page template draws each field with ``{{ form.<field>|as_crispy_field }}``;
the API sends that same server-rendered markup per field (so labels, widgets,
locked-by-RENAPER help and error feedback are the native ones) and the four
check-box groups as options. A native redirect becomes
``{"ok": true, "redirect": <Location>}`` and the queued messages (success,
provisioning notice) show on the destination like the HTML; an invalid form
returns 400 with the same payload. Responses are ``private, no-store``.
"""

from django.template import Context, Template
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie

from centrodeinfancia.views import (
    TrabajadorCentroInfanciaCreateView,
    TrabajadorCentroInfanciaUpdateView,
)
from centrodeinfancia.web_api import pending_messages
from centrodeinfancia.web_api_nomina import _plantilla
from centrodeinfancia.web_api_observaciones import _json, _ObservacionTransportMixin

PERMISO_ALTA = "centrodeinfancia.add_trabajador"
PERMISO_EDICION = "centrodeinfancia.change_trabajador"
MULTIPLES = (
    "capacitaciones_certificadas",
    "grupo_pertenencia",
    "lenguajes",
    "tipo_discapacidad",
)
_CRISPY = Template("{% load crispy_forms_tags %}{{ campo|as_crispy_field }}")


def _crispy(campo):
    """``{{ form.<campo>|as_crispy_field }}``, the markup of the native page."""
    return _CRISPY.render(Context({"campo": campo}))


def _con_guion(contexto, expresion):
    """``{{ expresion|default:'-' }}`` as the read-only institution inputs show it."""
    return _plantilla("{{ " + expresion + "|default:'-' }}").render(contexto)


def _errores(errores):
    return [str(error) for error in errores]


def _opciones(campo):
    return [
        {
            "id": opcion.id_for_label,
            "value": str(opcion.data["value"]),
            "label": str(opcion.choice_label),
            "checked": bool(opcion.data["selected"]),
        }
        for opcion in campo
    ]


def _campos(form):
    crispy, multiples = {}, {}
    for campo in form:
        if campo.name in MULTIPLES:
            multiples[campo.name] = {
                "label": str(campo.label),
                "options": _opciones(campo),
                "errors": _errores(campo.errors),
            }
        else:
            crispy[campo.name] = _crispy(campo)
    return crispy, multiples


def _institucion(centro):
    contexto = Context({"centro": centro}, autoescape=False)
    return {
        "id": centro.pk,
        "nombre": str(centro.nombre),
        "url": reverse("centrodeinfancia_detalle", args=[centro.pk]),
        "provincia": _con_guion(contexto, "centro.provincia"),
        "departamento": _con_guion(contexto, "centro.departamento"),
        "municipio": _con_guion(contexto, "centro.municipio"),
        "localidad": _con_guion(contexto, "centro.localidad"),
        "codigo_cdi": _con_guion(contexto, "centro.codigo_cdi"),
    }


def _ciudadano(ciudadano):
    return {
        "id": ciudadano.pk,
        "apellido": str(ciudadano.apellido),
        "nombre": str(ciudadano.nombre),
        "documento": _con_guion(
            Context({"c": ciudadano}, autoescape=False), "c.documento"
        ),
    }


def _busqueda(context):
    """The DNI search block of ``trabajador_form.html`` (create only)."""
    seleccionado = context.get("selected_ciudadano")
    token = context.get("renaper_prefill_token")
    return {
        "query": str(context.get("query") or ""),
        "ciudadanos": [_ciudadano(c) for c in context.get("ciudadanos") or []],
        "selected": _ciudadano(seleccionado) if seleccionado else None,
        "no_resultados": bool(context.get("no_resultados")),
        "renaper_precarga": bool(context.get("renaper_precarga")),
        "renaper_prefill_token": str(token) if token else None,
    }


class _TrabajadorTransportMixin(_ObservacionTransportMixin):
    """The form payload of the native context; an invalid form is a 400."""

    def form_invalid(self, form):
        return self.render_to_response(self.get_context_data(form=form), status=400)

    def render_to_response(self, context, **response_kwargs):
        form = context["form"]
        es_edicion = bool(context["is_edit"])
        crispy, multiples = _campos(form)
        centro = context["centro"]
        return _json(
            {
                "is_edit": es_edicion,
                "centro": _institucion(centro),
                "search": None if es_edicion else _busqueda(context),
                "mostrar_formulario": bool(
                    es_edicion or context.get("mostrar_formulario")
                ),
                "non_field_errors": _errores(form.non_field_errors()),
                "fields": crispy,
                "multiples": multiples,
                "ciudadano_id": (
                    context["selected_ciudadano"].pk
                    if not es_edicion and context.get("selected_ciudadano")
                    else None
                ),
                "urls": {
                    "cancelar": reverse("centrodeinfancia_detalle", args=[centro.pk]),
                    "departamentos": reverse(
                        "centrodeinfancia_ajax_load_departamentos_ipi"
                    ),
                    "municipios": reverse("ajax_load_municipios"),
                    "localidades": reverse("ajax_load_localidades"),
                },
                "messages": pending_messages(self.request),
            },
            status=response_kwargs.get("status", 200),
        )


@method_decorator(ensure_csrf_cookie, name="dispatch")
@method_decorator(csrf_protect, name="dispatch")
class TrabajadorCrearWebView(
    _TrabajadorTransportMixin, TrabajadorCentroInfanciaCreateView
):
    """``/api/web/cdi/centros/<pk>/trabajadores/crear/``: native create."""

    permission_code = PERMISO_ALTA


@method_decorator(ensure_csrf_cookie, name="dispatch")
@method_decorator(csrf_protect, name="dispatch")
class TrabajadorEditarWebView(
    _TrabajadorTransportMixin, TrabajadorCentroInfanciaUpdateView
):
    """``/api/web/cdi/centros/<pk>/trabajadores/<trabajador_id>/editar/``: native edit."""

    permission_code = PERMISO_EDICION
