"""Alta y edición de un ciudadano para React (C05.02, G1 v1).

``/api/web/ciudadanos/crear/`` y ``/api/web/ciudadanos/<pk>/editar/`` los sirve el
core y corren ``CiudadanosCreateView`` / ``CiudadanosUpdateView`` con ``dispatch``:
login y permiso (``add_ciudadano`` / ``change_ciudadano``, 403) primero y, en la
edición, el 404 después, como la vista nativa. El ``GET`` proyecta el contexto del
formulario que imprime ``ciudadano_form.html``; con ``?dni=`` en el alta corre la
búsqueda nativa (``obtener_datos_ciudadano_desde_renaper``: en las pruebas se
reemplaza, nunca se llama a RENAPER). El ``POST`` (multipart, como el formulario
nativo) corre el ``post()`` nativo: ``CiudadanoForm``, normalización de identidad,
``IntegrityError`` de identidad única, foto en el almacenamiento nativo y mensaje en
cola. Un 302 pasa a ``{"ok": true, "redirect": ...}`` y un formulario rechazado a
un 400 con el formulario ligado, sin escribir nada.
"""

from django import forms
from django.http import Http404
from django.urls import reverse
from django.utils.cache import patch_cache_control, patch_vary_headers
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import NotFound
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.views import APIView

from ciudadanos.views import CiudadanosCreateView, CiudadanosUpdateView
from ciudadanos.web_ficha import pending_messages
from core.web_gate import WebGatePermission


def _texto(valor):
    return "" if valor is None else str(getattr(valor, "pk", valor))


def _tipo(campo):
    widget = campo.widget
    if isinstance(widget, forms.CheckboxInput):
        return "checkbox"
    if isinstance(widget, forms.ClearableFileInput):
        return "file"
    if isinstance(widget, forms.Select):
        return "select"
    if isinstance(widget, forms.Textarea):
        return "textarea"
    return getattr(widget, "input_type", "text")


def _campo(form, nombre):
    campo = form.fields[nombre]
    ligado = form[nombre]
    tipo = _tipo(campo)
    valor = ligado.value()
    proyeccion = {
        "name": nombre,
        "label": str(ligado.label),
        "required": campo.required,
        "disabled": campo.disabled,
        "help_text": str(campo.help_text or ""),
        "widget": tipo,
        "attrs": {
            clave: str(atributo)
            for clave, atributo in ligado.build_widget_attrs(
                dict(campo.widget.attrs)
            ).items()
            if clave in ("maxlength", "min", "max", "step", "rows", "cols")
            and atributo is not None
        },
    }
    if tipo == "checkbox":
        proyeccion["value"] = bool(valor)
    elif tipo == "file":
        proyeccion["value"] = ""
        actual = form.instance.foto if form.instance.pk else None
        widget = campo.widget
        proyeccion["current"] = (
            {
                "name": str(actual.name),
                "url": actual.url,
                "initial_text": str(widget.initial_text),
                "clear_label": str(widget.clear_checkbox_label),
                "input_text": str(widget.input_text),
            }
            if actual
            else None
        )
    elif tipo == "date":
        # ``DateInput`` imprime el formato local; la plantilla completa el valor ISO.
        proyeccion["value"] = campo.widget.format_value(valor) or ""
    else:
        proyeccion["value"] = _texto(valor)
    if tipo == "select":
        proyeccion["choices"] = [
            {"value": _texto(getattr(opcion, "value", opcion)), "label": str(texto)}
            for opcion, texto in campo.choices
        ]
    return proyeccion


def _errores(form):
    datos = form.errors.get_json_data()
    return {
        "errors": {
            nombre: [str(item["message"]) for item in items]
            for nombre, items in datos.items()
            if nombre != "__all__"
        },
        "non_field_errors": [str(item["message"]) for item in datos.get("__all__", [])],
    }


def _revision(objeto):
    """Aviso de revisión de identidad de la edición (``object.requiere_revision_manual``)."""
    if objeto is None or not objeto.requiere_revision_manual:
        return None
    tipo = objeto.tipo_registro_identidad
    motivo = descripcion = ""
    if tipo == "SIN_DNI":
        if objeto.motivo_sin_dni:
            motivo = objeto.get_motivo_sin_dni_display()
        descripcion = objeto.motivo_sin_dni_descripcion or ""
    elif tipo == "DNI_NO_VALIDADO_RENAPER":
        if objeto.motivo_no_validacion_renaper:
            motivo = objeto.get_motivo_no_validacion_renaper_display()
        descripcion = objeto.motivo_no_validacion_descripcion or ""
    return {
        "sin_dni": tipo == "SIN_DNI",
        "no_validado": tipo == "DNI_NO_VALIDADO_RENAPER",
        "motivo_texto": motivo,
        "descripcion_texto": descripcion,
    }


def _proyectar(contexto, request):
    form = contexto["form"]
    objeto = contexto.get("object")
    existe = objeto is not None and objeto.pk is not None
    fecha = objeto.fecha_nacimiento if existe else None
    return {
        "modo": "editar" if existe else "crear",
        "fields": [_campo(form, nombre) for nombre in form.fields],
        **_errores(form),
        "fecha_nacimiento_inicial": fecha.strftime("%Y-%m-%d") if fecha else "",
        "revision": _revision(objeto) if existe else None,
        "busqueda": (
            None
            if existe
            else {
                "dni": request.GET.get("dni", ""),
                "sexo": contexto["sexo_busqueda"],
                "sexos": [
                    {"value": valor, "label": etiqueta}
                    for valor, etiqueta in contexto["sexo_busqueda_choices"]
                ],
            }
        ),
        "urls": {
            "volver": objeto.get_absolute_url() if existe else reverse("ciudadanos"),
            "municipios": reverse("ajax_load_municipios"),
            "localidades": reverse("ajax_load_localidades"),
            "address_preview": reverse("address_preview"),
        },
        "messages": pending_messages(request),
    }


class _CiudadanoFormWebView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [WebGatePermission]
    renderer_classes = [JSONRenderer]
    parser_classes = [MultiPartParser, FormParser]
    http_method_names = ["get", "post"]
    vista_nativa = None

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        patch_cache_control(response, private=True, no_store=True)
        patch_vary_headers(response, ("Cookie",))
        return response

    def _despachar(self, request, **kwargs):
        # pylint: disable-next=not-callable
        vista = self.vista_nativa()
        # pylint: disable-next=protected-access
        django_request = request._request
        vista.setup(django_request, **kwargs)
        try:
            return vista.dispatch(django_request, **kwargs)
        except Http404 as exc:
            raise NotFound() from exc

    def get(self, request, **kwargs):
        respuesta = self._despachar(request, **kwargs)
        return Response(_proyectar(respuesta.context_data, request))

    def post(self, request, **kwargs):
        respuesta = self._despachar(request, **kwargs)
        if respuesta.status_code != 302:
            return Response(_proyectar(respuesta.context_data, request), status=400)
        return Response({"ok": True, "redirect": respuesta["Location"]})


class CiudadanoCrearWebView(_CiudadanoFormWebView):
    vista_nativa = CiudadanosCreateView


class CiudadanoEditarWebView(_CiudadanoFormWebView):
    vista_nativa = CiudadanosUpdateView
