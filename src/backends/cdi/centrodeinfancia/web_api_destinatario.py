"""Web API (G1 v1) of the CDI destinatario create and edit screens (CDI nomina) for React.

Session transport over the native views: each API view inherits
``NominaCentroInfanciaCreateView`` / ``NominaCentroInfanciaEditView``, so the
scoped centre or ficha (404 outside the actor's scope), the DNI search (local
citizens first, RENAPER only as the native view does it), the signed 15-minute
RENAPER prefill token, ``NominaCentroInfanciaDestinatariosForm`` with its required,
locked and conditional fields, the citizen creation, the nomina lock, the
messages and the CDI-A3 read-only veto for SIMEPI auditors stay the native ones.
Order of checks:

1. G1 (``WebGatePermission``): 401/403 JSON, or the signed attestation.
2. The same permission code as the URL decorator in ``centrodeinfancia/urls.py``
   (``add_nominacentroinfancia`` and ``change_nominacentroinfancia``).
3. The native dispatch.

The API sends the fields ``destinatario_form.html`` draws (``CAMPOS``), each with
the data its crispy markup needs (label, widget, value, choices, errors); the
check-box groups as options; and the RENAPER blocks. A native redirect becomes
``{"ok": true, "redirect": <Location>}`` and the queued messages show on the
destination like the HTML. A POST that is answered with the form again (an
invalid form, a refused save) returns 400 with the same payload. Responses are
``private, no-store``.
"""

from django.forms import CheckboxInput, Textarea
from django.http import JsonResponse
from django.template import Context, Template
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie

from centrodeinfancia.services_renaper_bloques import (
    BLOQUE_NINO,
    BLOQUE_RESPONSABLE_1,
    BLOQUE_RESPONSABLE_2,
)
from centrodeinfancia.views import (
    NominaCentroInfanciaCreateView,
    NominaCentroInfanciaEditView,
)
from centrodeinfancia.web_api import pending_messages
from centrodeinfancia.web_api_formularios import (
    TransporteFormularioMixin,
    bloque_renaper_web,
    campo_web,
    privada,
)

PERMISO_ALTA = "centrodeinfancia.add_nominacentroinfancia"
PERMISO_EDICION = "centrodeinfancia.change_nominacentroinfancia"
MULTIPLES = (
    "grupo_pertenencia",
    "lenguajes",
    "tipo_discapacidad",
    "alergias_alimentarias",
)
VACUNAS = (
    "bcg",
    "neumococo",
    "quintuple",
    "polio",
    "rotavirus",
    "meningococo",
    "antigripal",
    "hepatitis_a",
    "triple_viral",
    "varicela",
    "triple_bacteriana_celular",
    "triple_bacteriana_acelular",
    "sincicial_respiratorio",
    "fiebre_amarilla",
)
# The fields ``destinatario_form.html`` draws, in template order. Nothing else is
# sent, so the page posts exactly what the native form posts.
CAMPOS = (
    "estado",
    "tipo_registro",
    "fecha_registro",
    "trabajador_registra",
    "apellido",
    "nombre",
    "fecha_nacimiento",
    "edad_calculada",
    "edad_unidad",
    "sexo",
    "tipo_documentacion",
    "dni",
    "cuit_nino",
    "sin_cuil_nino",
    "pais_nacimiento",
    "nacionalidad",
    "sala",
    "responsable_legal_1_tipo_documentacion",
    "responsable_legal_1_dni",
    "responsable_legal_1_apellido",
    "responsable_legal_1_nombre",
    "responsable_legal_1_fecha_nacimiento",
    "responsable_legal_1_cuit",
    "responsable_legal_1_sin_cuil",
    "responsable_legal_1_sexo_registral",
    "responsable_legal_1_nacionalidad",
    "responsable_legal_1_relacion",
    "responsable_legal_1_telefono",
    "responsable_legal_1_pais_nacimiento",
    "responsable_legal_1_nivel_educativo",
    "responsable_legal_1_consentimiento",
    "responsable_legal_2_tipo_documentacion",
    "responsable_legal_2_dni",
    "responsable_legal_2_apellido",
    "responsable_legal_2_nombre",
    "responsable_legal_2_fecha_nacimiento",
    "responsable_legal_2_cuit",
    "responsable_legal_2_sexo_registral",
    "responsable_legal_2_nacionalidad",
    "responsable_legal_2_relacion",
    "responsable_legal_2_telefono",
    "responsable_legal_2_pais_nacimiento",
    "responsable_legal_2_nivel_educativo",
    "responsable_legal_2_consentimiento",
    "calle_domicilio",
    "altura_domicilio",
    "piso_domicilio",
    "departamento_domicilio",
    "tipo_barrio",
    "provincia_domicilio",
    "departamento",
    "decil_ipi",
    "municipio_domicilio",
    "localidad_domicilio",
    "convivientes",
    "pueblo_originario_cual",
    "necesito_interprete",
    "tiene_discapacidad",
    "posee_cud",
    "numero_cud",
    "recibe_apoyo_desarrollo",
    "cobertura_salud",
    "controles_sanitarios_ultimo_anio",
    "calendario_vacunacion_al_dia",
    "talla",
    "peso",
    "longitud_acostado",
    "perimetro_cefalico",
    "lactancia",
    "anses_auh",
    "anses_aue",
    "anses_acsi",
    "anses_acn",
    *(
        f"vacuna_{codigo}_{sufijo}"
        for codigo in VACUNAS
        for sufijo in ("dosis", "fecha")
    ),
    "observaciones",
)


def _texto(contexto, fuente):
    """Render a template fragment of the native page without escaping (React escapes)."""
    return Template(fuente).render(Context(contexto, autoescape=False))


def _centro(centro):
    contexto = {"centro": centro}
    return {
        "id": centro.pk,
        "nombre": str(centro.nombre),
        "url": reverse("centrodeinfancia_nomina_ver", args=[centro.pk]),
        "nombre_visible": _texto(contexto, '{{ centro.nombre|default:"—" }}'),
        "codigo_cdi": _texto(contexto, '{{ centro.codigo_cdi|default:"—" }}'),
        "provincia": _texto(contexto, '{{ centro.provincia|default:"—" }}'),
        "departamento": _texto(
            contexto,
            "{% if centro.departamento %}{{ centro.departamento.nombre }} "
            "({{ centro.departamento.codigo_departamento }}){% else %}—{% endif %}",
        ),
        "municipio": _texto(contexto, '{{ centro.municipio|default:"—" }}'),
        "localidad": _texto(contexto, '{{ centro.localidad|default:"—" }}'),
    }


def _ciudadano(ciudadano):
    return {
        "id": ciudadano.pk,
        "apellido": str(ciudadano.apellido),
        "nombre": str(ciudadano.nombre),
        "documento": _texto({"c": ciudadano}, '{{ c.documento|default:"-" }}'),
    }


def _busqueda(context):
    """The DNI search block of ``destinatario_form.html`` (create only)."""
    token = context.get("renaper_prefill_token")
    return {
        "query": str(context.get("query") or ""),
        "ciudadanos": [_ciudadano(c) for c in context.get("ciudadanos") or []],
        "no_resultados": bool(context.get("no_resultados")),
        "renaper_precarga": bool(context.get("renaper_precarga")),
        "renaper_prefill_token": str(token) if token else None,
    }


def _valor_seleccionado(bound):
    """The option the native ``<select>`` marks as selected (``""`` when none)."""
    for opcion in bound.subwidgets:
        if opcion.data["selected"]:
            return str(opcion.data["value"])
    return ""


def _campo(form, nombre):
    """``campo_web`` plus what the destinatario page needs to draw the control."""
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


def _bloques(form, tokens, es_edicion):
    return {
        BLOQUE_NINO: (
            bloque_renaper_web(
                form, BLOQUE_NINO, tokens.get(BLOQUE_NINO, ""), permite_cambiar=False
            )
            if es_edicion or form.bloques_verificados_renaper[BLOQUE_NINO]
            else None
        ),
        BLOQUE_RESPONSABLE_1: bloque_renaper_web(
            form,
            BLOQUE_RESPONSABLE_1,
            tokens.get(BLOQUE_RESPONSABLE_1, ""),
            permite_cambiar=True,
        ),
        BLOQUE_RESPONSABLE_2: bloque_renaper_web(
            form,
            BLOQUE_RESPONSABLE_2,
            tokens.get(BLOQUE_RESPONSABLE_2, ""),
            permite_cambiar=True,
            opcional=True,
        ),
    }


class _DestinatarioTransportMixin(TransporteFormularioMixin):
    """The form payload of the native context; a rejected POST is a 400."""

    def render_to_response(self, context, **response_kwargs):
        form = context["form"]
        es_edicion = bool(context.get("is_edit"))
        centro = context["centro"]
        seleccionado = context.get("selected_ciudadano")
        token = context.get("renaper_prefill_token")
        cuerpo = {
            "is_edit": es_edicion,
            "centro": _centro(centro),
            "search": None if es_edicion else _busqueda(context),
            "mostrar_formulario": bool(es_edicion or context.get("mostrar_formulario")),
            "selected": _ciudadano(seleccionado) if seleccionado else None,
            "renaper_prefill_token": str(token) if token else None,
            "non_field_errors": [str(e) for e in form.non_field_errors()],
            "fields": [
                _campo(form, nombre) for nombre in CAMPOS if nombre not in MULTIPLES
            ],
            "multiples": {nombre: _multiple(form[nombre]) for nombre in MULTIPLES},
            "renaper": _bloques(form, context.get("renaper_tokens") or {}, es_edicion),
            "urls": {
                "cancelar": reverse("centrodeinfancia_nomina_ver", args=[centro.pk]),
                "departamentos": reverse(
                    "centrodeinfancia_ajax_load_departamentos_ipi"
                ),
                "municipios": reverse("ajax_load_municipios"),
                "localidades": reverse("ajax_load_localidades"),
            },
            "messages": pending_messages(self.request),
        }
        # Every answer to a POST that is not a redirect is the form again: a rejection.
        estado = 400 if self.request.method == "POST" else 200
        return privada(JsonResponse(cuerpo, status=estado))


@method_decorator(ensure_csrf_cookie, name="dispatch")
@method_decorator(csrf_protect, name="dispatch")
class DestinatarioCrearWebView(
    _DestinatarioTransportMixin, NominaCentroInfanciaCreateView
):
    """``/api/web/cdi/centros/<pk>/nomina/crear/``: native create."""

    permission_codes = (PERMISO_ALTA,)


@method_decorator(ensure_csrf_cookie, name="dispatch")
@method_decorator(csrf_protect, name="dispatch")
class DestinatarioEditarWebView(
    _DestinatarioTransportMixin, NominaCentroInfanciaEditView
):
    """``/api/web/cdi/centros/<pk>/nomina/<nomina_id>/editar/``: native edit."""

    permission_codes = (PERMISO_EDICION,)
