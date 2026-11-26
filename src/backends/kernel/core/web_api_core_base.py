"""Base común de la API web del core (``/api/web/core/``, T01-T07).

Las pantallas del núcleo (novedades, arquitectura, programas, papelera) las sirve el
core con la misma puerta que ``/api/web/insumos/``: sesión de Django y
``WebGatePermission``. Cada vista web ejecuta la vista nativa y proyecta su contexto;
no reescribe sus reglas.
"""

from html.parser import HTMLParser

from django import forms
from django.contrib import messages
from django.http import Http404
from django.utils.cache import patch_cache_control, patch_vary_headers
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import NotFound
from rest_framework.parsers import FormParser
from rest_framework.renderers import JSONRenderer
from rest_framework.views import APIView

from core.web_gate import WebGatePermission

MESSAGE_LEVELS = {
    messages.SUCCESS: "success",
    messages.ERROR: "error",
    messages.WARNING: "warning",
    messages.INFO: "info",
}
DETAIL_FORBIDDEN = "No tiene permisos para esta acción."


def pending_messages(request):
    """Consume los mensajes en cola igual que la página nativa."""
    return [
        {"message": str(m), "level": MESSAGE_LEVELS.get(m.level, "info")}
        for m in messages.get_messages(request)
    ]


def native_view(view_class, request, **kwargs):
    """Instancia una vista nativa sobre el ``HttpRequest`` real, sin ejecutar su ``dispatch``."""
    view = view_class()
    # pylint: disable-next=protected-access
    view.setup(request._request, **kwargs)
    return view


def native_object(view):
    """``get_object()`` nativo; su 404 es el 404 de la API."""
    try:
        return view.get_object()
    except Http404 as exc:
        raise NotFound() from exc


@method_decorator(ensure_csrf_cookie, name="dispatch")
class CoreWebView(APIView):
    """Sesión + puerta web del core; respuestas privadas y sin caché."""

    authentication_classes = [SessionAuthentication]
    permission_classes = [WebGatePermission]
    renderer_classes = [JSONRenderer]
    parser_classes = [FormParser]
    http_method_names = ["get", "post", "head", "options"]

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        patch_cache_control(response, private=True, no_store=True)
        patch_vary_headers(response, ("Cookie",))
        return response


def _widget_kind(field):
    widget = field.widget
    if isinstance(widget, forms.CheckboxInput):
        return "checkbox"
    if isinstance(widget, forms.Select):
        return "select"
    if isinstance(widget, forms.Textarea):
        return "textarea"
    return getattr(widget, "input_type", "text")


def _text(value):
    return "" if value is None else str(getattr(value, "pk", value))


class _FirstTag(HTMLParser):
    """Atributos de la primera etiqueta del widget que imprime Django."""

    def __init__(self):
        super().__init__()
        self.attrs = None

    def handle_starttag(self, tag, attrs):
        if self.attrs is None:
            self.attrs = {key: value or "" for key, value in attrs}


NATIVE_ATTRS = (
    "class",
    "type",
    "placeholder",
    "maxlength",
    "rows",
    "cols",
    "aria-invalid",
    "aria-describedby",
)


def native_attrs(bound):
    """Los atributos del widget tal como los imprime la plantilla nativa (``{{ field }}``)."""
    parser = _FirstTag()
    parser.feed(str(bound))
    return {
        key: parser.attrs[key] for key in NATIVE_ATTRS if key in (parser.attrs or {})
    }


def project_form(form):
    """Campos del formulario nativo en el orden en que la plantilla los imprime."""
    fields = []
    for name in form.fields:
        field = form.fields[name]
        bound = form[name]
        kind = _widget_kind(field)
        attrs = native_attrs(bound)
        item = {
            "name": name,
            "id": bound.id_for_label,
            "label": str(bound.label),
            "widget": kind,
            "required": bool(field.required and form.use_required_attribute),
            "attrs": attrs,
            "value": (
                bool(bound.value()) if kind == "checkbox" else _text(bound.value())
            ),
            "errors": [str(error) for error in bound.errors],
        }
        if kind == "select":
            item["choices"] = [
                {"value": _text(value), "label": str(label)}
                for value, label in field.choices
            ]
        fields.append(item)
    return fields
