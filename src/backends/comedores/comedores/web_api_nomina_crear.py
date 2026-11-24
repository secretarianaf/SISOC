"""Web API (G1 v1) of the comedor "Agregar a Nómina" screen served by React (CO01).

``/api/web/comedores/nomina-crear/`` keeps the permission code of the native URLs
(``comedores.add_nomina``, superuser bypass included) and runs the native views itself
(``NominaCreateView`` for a convenio with admission, ``NominaDirectaCreateView`` for a direct
nómina): the scoped comedor/admission lookup (404 outside the scope, 404 for a direct nómina of a
comedor that needs an admission), the citizen search with the RENAPER lookup, the three forms,
``ComedorService`` and the PNUD attendance sync stay the native ones. A native redirect becomes
``{"ok": true, "redirect": ...}``; a rejected POST returns 400 with the bound forms, writing
nothing. The view reads ``request.POST`` itself, so only what the native template posts counts.
"""

from html.parser import HTMLParser

from crispy_forms.templatetags.crispy_forms_filters import as_crispy_field
from django.contrib import messages
from django.http import Http404
from django.template import Context, Template
from django.urls import reverse
from rest_framework.exceptions import NotFound
from rest_framework.response import Response

from comedores.views.nomina import NominaCreateView, NominaDirectaCreateView
from core.web_gate import WebGatePermission
from intervenciones.web_api import NativeWebView, requires_any

FORMATOS = ("multipart/form-data", "application/x-www-form-urlencoded")
ADD_PERMISSIONS = ["comedores.add_nomina"]
MODAL_FIELDS = (
    "pertenece_comunidad_indigena",
    "en_situacion_de_calle",
    "persona_con_celiaquia",
)
# The label of an activity checkbox in ``nomina_form.html``.
_ACTIVIDAD = Template(
    "{{ a.catalogo_actividad }} - {{ a.dia_actividad }} {{ a.horario_actividad }}"
)


class _Controls(HTMLParser):
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
            for clave in ("id", "name", "value", "checked", "selected"):
                values.pop(clave, None)
            self.controls.append({"tag": tag, "attrs": values})


def _tipo(controles):
    if not controles:
        return "checkboxmultiple"
    primero = controles[0]
    if primero["tag"] in ("select", "textarea"):
        return primero["tag"]
    if primero["attrs"].get("type") == "checkbox":
        return "checkboxmultiple" if len(controles) > 1 else "checkbox"
    return "input"


def _campo(form, name):
    bound = form[name]
    parser = _Controls(bound.auto_id)
    parser.feed(str(as_crispy_field(bound)))
    tipo = _tipo(parser.controls)
    valor = bound.value()
    campo = {
        "name": bound.html_name,
        "id": bound.auto_id,
        "label": str(bound.label),
        "required": bound.field.required,
        "kind": tipo,
        "attrs": (
            {}
            if tipo == "checkboxmultiple" or not parser.controls
            else parser.controls[0]["attrs"]
        ),
        "help_text": str(bound.help_text or ""),
        "errors": [str(error) for error in form.errors.get(name, [])],
    }
    if tipo == "checkbox":
        campo["value"] = bool(valor)
    elif tipo == "checkboxmultiple":
        elegidos = {str(item) for item in (valor or [])}
        campo["value"] = sorted(elegidos)
        campo["choices"] = [
            {
                "value": str(actividad.pk),
                "label": _ACTIVIDAD.render(Context({"a": actividad})),
                "checked": str(actividad.pk) in elegidos,
            }
            for actividad in bound.field.queryset
        ]
    else:
        campo["value"] = "" if valor is None else str(valor)
        if tipo == "select":
            campo["choices"] = [
                {"value": str(v), "label": str(etiqueta)}
                for v, etiqueta in bound.field.choices
            ]
    return campo


def _form(form):
    return {
        "fields": [_campo(form, name) for name in form.fields],
        "non_field_errors": [str(error) for error in form.non_field_errors()],
    }


def _plano(valor):
    return "" if valor is None else str(valor)


def _ciudadano(c):
    return {
        "id": c.id,
        "apellido": c.apellido or "",
        "nombre": c.nombre or "",
        "documento": _plano(c.documento),
        "tipo_registro": c.tipo_registro_identidad,
        "revision": bool(c.requiere_revision_manual),
        "comunidad_indigena": _plano(c.pertenece_comunidad_indigena),
        "situacion_calle": _plano(c.en_situacion_de_calle),
        "celiaquia": _plano(c.persona_con_celiaquia),
    }


def _pagina(contexto, request):
    comedor = contexto["object"]
    cupo = contexto.get("cupo_alimentario")
    pnud = bool(contexto["mostrar_asistencia_pnud"])
    actividades = contexto["actividades_pnud"]
    return {
        "comedor": {
            "id": comedor.id,
            "nombre": comedor.nombre,
            "url": reverse("comedor_detalle", args=[comedor.id]),
        },
        "query": request.GET.get("query", ""),
        "cupo": (
            {
                "completo": bool(cupo["completo"]),
                "ocupados": cupo["ocupados"],
                "tope": cupo["tope"],
            }
            if cupo
            else None
        ),
        "has_activities": bool(actividades),
        "ciudadanos": [_ciudadano(c) for c in contexto["ciudadanos"]],
        "show_form": bool(contexto["mostrar_form_ciudadano"]),
        "renaper": bool(contexto["renaper_precarga"]),
        "mode": contexto["modo_creacion"],
        "form_ciudadano": _form(contexto["form_ciudadano"]),
        "form_sin_dni": _form(contexto["form_ciudadano_sin_dni"]),
        "form_extra": _form(contexto["form_nomina_extra"]),
        "modal_fields": [
            _campo(contexto["form_datos_ciudadano"], name) for name in MODAL_FIELDS
        ],
        "estados": [
            {"value": value, "label": str(label)}
            for value, label in contexto["estados"]
        ],
        "pnud": pnud,
        "actividades": (
            [
                {"id": a.id, "label": _ACTIVIDAD.render(Context({"a": a}))}
                for a in actividades
            ]
            if pnud
            else []
        ),
        "messages": [
            {"message": str(m), "tags": m.tags} for m in messages.get_messages(request)
        ],
    }


class _NominaCrearWebView(NativeWebView):
    permission_classes = [WebGatePermission, requires_any(ADD_PERMISSIONS)]
    http_method_names = ["get", "head", "post"]
    view_class = None

    def _vista(self, request, **kwargs):
        vista = self.native(self.view_class, request, **kwargs)
        vista.object = None
        return vista

    def get(self, request, **kwargs):
        vista = self._vista(request, **kwargs)
        try:
            contexto = vista.get_context_data()
        except Http404 as exc:
            raise NotFound() from exc
        return Response(_pagina(contexto, request))

    def post(self, request, **kwargs):
        # ``Request.content_type`` keeps the multipart boundary; Django strips it.
        # pylint: disable-next=protected-access
        if request._request.content_type not in FORMATOS:
            return Response({"detail": "Formato de solicitud no admitido."}, status=415)
        vista = self._vista(request, **kwargs)
        try:
            # pylint: disable-next=protected-access
            respuesta = vista.post(request._request)
        except Http404 as exc:
            raise NotFound() from exc
        if respuesta.status_code == 302:
            return Response({"ok": True, "redirect": respuesta["Location"]})
        return Response(_pagina(respuesta.context_data, request), status=400)


class NominaCrearAdmisionWebView(_NominaCrearWebView):
    """``/api/web/comedores/nomina-crear/<pk>/admision/<admision_pk>/``."""

    view_class = NominaCreateView


class NominaCrearDirectaWebView(_NominaCrearWebView):
    """``/api/web/comedores/nomina-crear/<pk>/``."""

    view_class = NominaDirectaCreateView
