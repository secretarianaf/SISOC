"""Web API (G1 v1) of the CDF centre create, edit and soft delete (CDF04.02).

Same access chain as ``centrodefamilia.web_api``: G1 session and web
prerequisites, then ``centrodefamilia.view_centro`` (``permissions_any_required``
predicate). After that each endpoint runs the native view itself:

- create: ``CentroCreateView`` (only ``view_centro``; ``can_add`` limits the
  list button, not the view), ``?faro=`` initial values, disabled fields and
  the ``faro_asociado_id`` assignment of ``form_valid``;
- edit and delete: the native ``dispatch`` rule (referente FK, superuser or
  ``auth.role_cdf_sse``; an active ``AccesoCDF`` is not enough) is evaluated
  before the body is read;
- delete: ``SoftDeleteDeleteViewMixin`` (``instance.delete(user, cascade=True)``)
  and its ``cascade_preview``.

The native ``post()`` saves, queues the success message and redirects; the API
answers that redirect as JSON (``redirect`` ``list`` or ``detail``) and the
React page returns to the native URL, where the queued message shows once.
An invalid form answers 400 with the bound values and errors. No retries.
"""

from django import forms
from django.urls import reverse
from rest_framework.response import Response

from centrodefamilia.views.centro import (
    CentroCreateView,
    CentroDeleteView,
    CentroUpdateView,
)
from centrodefamilia.web_api import CdfWebView, native_view, pending_messages

MESSAGES = {
    "create": "Centro creado exitosamente.",
    "update": "Centro actualizado correctamente.",
    "delete": "Centro dado de baja correctamente.",
}


class _GuardedUpdate(CentroUpdateView):
    """The native view; its GET only resolves the object after ``dispatch``."""

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()


class _GuardedDelete(CentroDeleteView):
    """The native delete view; its GET only resolves the object after ``dispatch``."""

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()


def _text(value):
    return "" if value is None else str(getattr(value, "pk", value))


def _widget(field):
    widget = field.widget
    if isinstance(widget, forms.HiddenInput):
        return "hidden"
    if isinstance(widget, forms.CheckboxInput):
        return "checkbox"
    if isinstance(widget, forms.ClearableFileInput):
        return "file"
    if isinstance(widget, forms.Select):
        return "select"
    return getattr(widget, "input_type", "text")


def _field(form, name):
    field = form.fields[name]
    bound = form[name]
    kind = _widget(field)
    value = bound.value()
    payload = {
        "name": name,
        "label": str(bound.label),
        "required": field.required,
        "disabled": field.disabled,
        "widget": kind,
        "help_text": str(field.help_text or ""),
        "value": bool(value) if kind == "checkbox" else _text(value),
        "attrs": {
            key: str(attr)
            for key, attr in bound.build_widget_attrs(dict(field.widget.attrs)).items()
            if key in ("maxlength", "min", "max", "step") and attr is not None
        },
    }
    if kind == "select":
        payload["choices"] = [
            {"value": _text(getattr(choice, "value", choice)), "label": str(label)}
            for choice, label in field.choices
        ]
    if kind == "file":
        payload["value"] = ""
        actual = form.initial.get(name) if not form.is_bound else value
        payload["current"] = (
            {"name": str(actual), "url": actual.url} if actual else None
        )
    return payload


def _errors(form):
    data = form.errors.get_json_data()
    return {
        "errors": {
            name: [
                {"message": str(item["message"]), "code": item["code"] or ""}
                for item in items
            ]
            for name, items in data.items()
            if name != "__all__"
        },
        "non_field_errors": [str(item["message"]) for item in data.get("__all__", [])],
    }


def _form_payload(form, request, *, cancel_url):
    return {
        "fields": [_field(form, name) for name in form.fields],
        "locked": [name for name, field in form.fields.items() if field.disabled],
        **_errors(form),
        "urls": {
            "cancel": cancel_url,
            "municipios": reverse("ajax_load_municipios"),
            "localidades": reverse("ajax_load_localidades"),
            "address_preview": reverse("address_preview"),
        },
        "messages": pending_messages(request),
    }


def _invalid(respuesta, request, cancel_url):
    form = respuesta.context_data["form"]
    return Response(_form_payload(form, request, cancel_url=cancel_url), status=400)


class CentroOptionsWebView(CdfWebView):
    """``GET /api/web/cdf/centros/options/?faro=``: the unbound create form."""

    def get(self, request):
        vista = native_view(CentroCreateView, request)
        vista.object = None
        return Response(_form_payload(vista.get_form(), request, cancel_url=""))


class CentroCrearWebView(CdfWebView):
    """``POST /api/web/cdf/centros/crear/[?faro=]``: ``CentroCreateView.post``."""

    http_method_names = ["post"]

    def post(self, request):
        vista = native_view(CentroCreateView, request)
        django_request = request._request  # pylint: disable=protected-access
        respuesta = vista.post(django_request)
        if respuesta.status_code != 302:
            return _invalid(respuesta, request, "")
        return Response(
            {
                "id": vista.object.pk,
                "message": MESSAGES["create"],
                "redirect": "list",
                "url": respuesta["Location"],
            },
            status=201,
        )


class CentroEditarWebView(CdfWebView):
    """``/api/web/cdf/centros/<pk>/editar/``: current values or the native save."""

    http_method_names = ["get", "post"]

    def _dispatch(self, request, pk):
        vista = native_view(_GuardedUpdate, request, pk=pk)
        django_request = request._request  # pylint: disable=protected-access
        return vista, vista.dispatch(django_request, pk=pk)

    def get(self, request, pk):
        vista, _ = self._dispatch(request, pk)
        return Response(_form_payload(vista.get_form(), request, cancel_url=""))

    def post(self, request, pk):
        vista, respuesta = self._dispatch(request, pk)
        if respuesta.status_code != 302:
            return _invalid(respuesta, request, "")
        return Response(
            {
                "id": vista.object.pk,
                "message": MESSAGES["update"],
                "redirect": "detail",
                "url": respuesta["Location"],
            }
        )


class CentroEliminarWebView(CdfWebView):
    """``/api/web/cdf/centros/<pk>/eliminar/``: cascade preview or soft delete."""

    http_method_names = ["get", "post"]

    def get(self, request, pk):
        vista = native_view(_GuardedDelete, request, pk=pk)
        django_request = request._request  # pylint: disable=protected-access
        vista.dispatch(django_request, pk=pk)
        context = vista.get_context_data()
        centro = vista.object
        return Response(
            {
                "id": centro.pk,
                "nombre": centro.nombre,
                "preview": context.get("cascade_preview"),
                "confirm_text": "Dar de baja",
                "cancel_text": context["cancel_text"],
                "urls": {"cancel": reverse("centro_detail", args=[centro.pk])},
                "messages": pending_messages(request),
            }
        )

    def post(self, request, pk):
        vista = native_view(_GuardedDelete, request, pk=pk)
        django_request = request._request  # pylint: disable=protected-access
        respuesta = vista.dispatch(django_request, pk=pk)
        return Response(
            {
                "message": MESSAGES["delete"],
                "redirect": "list",
                "url": respuesta["Location"],
            }
        )
