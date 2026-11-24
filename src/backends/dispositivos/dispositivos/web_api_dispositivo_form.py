"""Web API (G1 v1) of the Dispositivos create and edit screens for React.

Session transport over the native views: each API view inherits
``DispositivoCreateView`` / ``DispositivoUpdateView``, so the scoped object
(404 outside the actor's scope), ``DispositivoForm`` with its geography scope,
validators and uploads, the save and the success message stay the native ones.
Order of checks:

1. G1 (``WebGatePermission``): 401/403 JSON, or the signed attestation.
2. The same permission code as the URL decorator in ``dispositivos/urls.py``
   (``add_dispositivo`` and ``change_dispositivo``).
3. The native dispatch.

The API sends the fields ``dispositivos_form.html`` draws, each with the data
its crispy markup needs (label, widget, value, choices, errors), the check-box
groups as options and the five document slots. A native redirect becomes
``{"ok": true, "redirect": <Location>}`` and the queued message shows on the
destination like the HTML. A POST answered with the form again (an invalid
form) returns 400 with the same payload. The POST is URL-encoded or multipart
(the document uploads). Responses are ``private, no-store``.
"""

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.forms import Select, Textarea
from django.http import Http404, JsonResponse
from django.urls import reverse
from django.utils.cache import patch_cache_control, patch_vary_headers
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from rest_framework.exceptions import APIException

from core.decorators import permissions_any_required
from core.web_gate import WebGatePermission

from .validators import DOCUMENTACION_UPLOAD_FIELDS
from .views import DispositivoCreateView, DispositivoUpdateView
from .web_api import MESSAGE_LEVELS

PERMISO_ALTA = "dispositivos.add_dispositivo"
PERMISO_EDICION = "dispositivos.change_dispositivo"
SIN_PERMISO = "No tiene permisos para esta acción."
NO_ENCONTRADO = "No encontrado."
FORMATOS_ADMITIDOS = ("application/x-www-form-urlencoded", "multipart/form-data")
# Length of the ``upload_to`` prefix the template cuts from the saved name.
PREFIJO_NOMBRE_ARCHIVO = 27

MULTIPLES = (
    "dias_atencion",
    "horarios_funcionamiento",
    "poblacion_destinataria",
    "franja_etaria_destinataria",
    "modalidad_ingreso",
    "documentacion_ingreso",
    "requisitos_ingreso",
    "servicios_brindados",
    "tipos_actividades_formativas",
    "tipo_informacion_registrada",
    "infraestructura_disponible",
    "infraestructura_accesibilidad",
    "articulaciones_institucionales",
)
# The simple fields ``dispositivos_form.html`` draws, in template order. Nothing
# else is sent, so the page posts exactly what the native form posts.
CAMPOS = (
    "nombre_institucion",
    "tipo_gestion",
    "tipo_gestion_otra",
    "razon_social",
    "cuit_institucion",
    "calle",
    "altura",
    "provincia",
    "municipio",
    "localidad",
    "latitud",
    "longitud",
    "telefono_prefijo",
    "telefono_numero",
    "correo_electronico",
    "responsable_nombre_completo",
    "responsable_dni",
    "tipo_dispositivo",
    "tipo_dispositivo_otro",
    "modalidad_funcionamiento",
    "capacidad_total_plazas",
    "poblacion_destinataria_otro",
    "tiempo_permanencia_promedio",
    "tiempo_permanencia_otro",
    "modalidad_ingreso_otro",
    "documentacion_ingreso_otro",
    "requisitos_ingreso_otro",
    "servicios_brindados_otro",
    "ofrece_actividades_formativas",
    "tipos_actividades_formativas_otro",
    "actividades_certificacion_oficial",
    "registra_informacion_personas",
    "modo_registro",
    "modo_registro_otro",
    "tipo_informacion_registrada_otro",
    "infraestructura_disponible_otro",
    "infraestructura_accesibilidad_otro",
    "principales_limitaciones",
    "necesidades_prioritarias",
    "articulaciones_institucionales_otro",
    "observaciones_adicionales",
)


def mensajes_pendientes(request):
    """Consume the queued Django messages of a native request, as the HTML page does."""
    return [
        {"message": str(item), "level": MESSAGE_LEVELS.get(item.level, "info")}
        for item in messages.get_messages(request)
    ]


def privada(response):
    patch_cache_control(response, private=True, no_store=True)
    patch_vary_headers(response, ("Cookie",))
    return response


def json_privado(body, status=200):
    return privada(JsonResponse(body, status=status))


def puerta_g1(request):
    """``WebGatePermission`` for a Django view: the same 401/403 bodies as DRF."""
    try:
        WebGatePermission().has_permission(request, None)
    except APIException as exc:
        detail = exc.detail if isinstance(exc.detail, dict) else {"detail": exc.detail}
        response = json_privado(
            {key: str(value) for key, value in detail.items()}, exc.status_code
        )
        if exc.status_code == 401:
            response["WWW-Authenticate"] = "Session"
        return response
    return None


def _atributos(campo):
    widget = campo.widget
    atributos = {**campo.widget_attrs(widget), **widget.attrs}
    atributos.pop("class", None)
    return {
        clave: str(valor)
        for clave, valor in atributos.items()
        if valor not in (None, False)
    }


def _opciones(bound):
    """The ``<option>`` list the native ``<select>`` draws and the selected value."""
    contexto = bound.field.widget.get_context(bound.html_name, bound.value(), {})
    opciones, seleccionado = [], ""
    for _nombre, grupo, _indice in contexto["widget"]["optgroups"]:
        for opcion in grupo:
            opciones.append(
                {"value": str(opcion["value"]), "label": str(opcion["label"])}
            )
            if opcion["selected"] and not seleccionado:
                seleccionado = str(opcion["value"])
    return opciones, seleccionado


def _errores(bound, form):
    if not form.is_bound:
        return []
    return [
        {"message": error["message"], "code": error["code"]}
        for error in bound.errors.get_json_data()
    ]


def _campo(form, nombre):
    """One field as the crispy template renders it (label, widget, help, value)."""
    bound = form[nombre]
    campo = bound.field
    widget = campo.widget
    datos = {
        "name": nombre,
        "label": str(bound.label or ""),
        "required": bool(campo.required),
        "help_text": str(campo.help_text or ""),
        "attrs": _atributos(campo),
        "errors": _errores(bound, form),
    }
    if isinstance(widget, Select):
        opciones, valor = _opciones(bound)
        datos.update(widget="select", value=valor, choices=opciones)
    else:
        valor = widget.format_value(bound.value())
        datos.update(
            widget=(
                "textarea"
                if isinstance(widget, Textarea)
                else getattr(widget, "input_type", "text")
            ),
            value="" if valor is None else str(valor),
        )
    return datos


def _multiple(form, nombre):
    bound = form[nombre]
    return {
        "name": nombre,
        "label": str(bound.label or ""),
        "required": bool(bound.field.required),
        "help_text": str(bound.field.help_text or ""),
        "errors": [str(error) for error in bound.errors] if form.is_bound else [],
        "options": [
            {
                "id": opcion.id_for_label,
                "value": str(opcion.data["value"]),
                "label": str(opcion.choice_label),
                "checked": bool(opcion.data["selected"]),
            }
            for opcion in bound
        ],
    }


def _archivo(form, nombre):
    """One document slot as ``form.instance`` shows it (``saved`` is ``None`` when empty)."""
    guardado = getattr(form.instance, nombre)
    datos = {
        "name": nombre,
        "accept": _atributos(form.fields[nombre]).get("accept", ""),
        "saved": None,
    }
    if guardado:
        datos["saved"] = {
            "full_name": guardado.name,
            "label": guardado.name[PREFIJO_NOMBRE_ARCHIVO:],
            "url": guardado.url,
            "pdf": guardado.name[-4:].lower() == ".pdf",
        }
    return datos


class _TransporteDispositivoFormMixin:
    """G1, the URL permission and the native dispatch, as JSON."""

    permission_codes = ()
    http_method_names = ["get", "head", "post"]

    def dispatch(self, request, *args, **kwargs):
        response = puerta_g1(request)
        if response is not None:
            return response
        guardada = permissions_any_required(list(self.permission_codes))(
            lambda req: self._nativa(req, *args, **kwargs)
        )
        try:
            response = guardada(request)
        except PermissionDenied as exc:
            return json_privado({"detail": str(exc) or SIN_PERMISO}, 403)
        except Http404:
            return json_privado({"detail": NO_ENCONTRADO}, 404)
        if response.status_code == 302:
            convertida = JsonResponse({"ok": True, "redirect": response["Location"]})
            convertida.cookies = response.cookies
            response = convertida
        return privada(response)

    def _nativa(self, request, *args, **kwargs):
        if request.method.lower() not in self.http_method_names:
            return self.http_method_not_allowed(request, *args, **kwargs)
        if request.method == "POST" and request.content_type not in FORMATOS_ADMITIDOS:
            return JsonResponse(
                {"detail": "Formato de solicitud no admitido."}, status=415
            )
        return super().dispatch(request, *args, **kwargs)

    def render_to_response(self, context, **response_kwargs):
        form = context["form"]
        es_edicion = bool(form.instance.pk)
        cuerpo = {
            "is_edit": es_edicion,
            "has_errors": bool(form.errors),
            "fields": [_campo(form, nombre) for nombre in CAMPOS],
            "multiples": {nombre: _multiple(form, nombre) for nombre in MULTIPLES},
            "files": [_archivo(form, nombre) for nombre in DOCUMENTACION_UPLOAD_FIELDS],
            "breadcrumb": [
                {"text": item["text"], "url": item.get("url")}
                for item in context["breadcrumb_items"]
            ],
            "urls": {
                "listar": reverse("dispositivos_listar"),
                "municipios": reverse("ajax_load_municipios"),
                "localidades": reverse("ajax_load_localidades"),
                "address_preview": reverse("dispositivos_previsualizar_ubicacion"),
                "saved_location": (
                    reverse("dispositivos_ubicacion", args=[form.instance.pk])
                    if es_edicion
                    else ""
                ),
            },
            "messages": mensajes_pendientes(self.request),
        }
        # Every answer to a POST that is not a redirect is the form again: a rejection.
        estado = 400 if self.request.method == "POST" else 200
        return json_privado(cuerpo, status=estado)


@method_decorator(ensure_csrf_cookie, name="dispatch")
@method_decorator(csrf_protect, name="dispatch")
class DispositivoCrearWebView(_TransporteDispositivoFormMixin, DispositivoCreateView):
    """``/api/web/dispositivos/crear/``: native create."""

    permission_codes = (PERMISO_ALTA,)


@method_decorator(ensure_csrf_cookie, name="dispatch")
@method_decorator(csrf_protect, name="dispatch")
class DispositivoEditarWebView(_TransporteDispositivoFormMixin, DispositivoUpdateView):
    """``/api/web/dispositivos/<pk>/editar/``: native edit (scope 404)."""

    permission_codes = (PERMISO_EDICION,)
