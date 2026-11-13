"""Web API (G1 v1) of the CDF centre activity create and edit form (CDF-B).

Same access chain as ``centrodefamilia.web_api``: G1 session and web
prerequisites, then ``centrodefamilia.view_centro``. Nothing else is added or
removed (decision D1): the native ``ActividadCentroCreateView`` and
``ActividadCentroUpdateView`` only require login besides that URL guard, and
their own ``dispatch`` and object lookup run unchanged (a missing centre or
activity is 404).

The native ``post()`` runs ``ActividadCentroForm`` (dependent activity queryset,
FARO price rule, ``centro`` kwarg), saves, queues the success message and
redirects to the centre ficha. The dependent activity list is
loaded by the page from ``/ajax/actividades/`` exactly like ``centro_familia_categoria.js``. The API answers that redirect as JSON (``url``
plus the queued message, which stays queued for the native page); an invalid
form answers 400 with the bound values and errors. Nothing is retried.
"""

from django import forms
from rest_framework.response import Response

from centrodefamilia.views.actividad import (
    ActividadCentroCreateView,
    ActividadCentroUpdateView,
)
from centrodefamilia.web_api import CdfWebView, native_view, pending_messages
from centrodefamilia.web_api_actividades import peek_messages
from centrodefamilia.web_api_gestion import _errors, _field


def _form_field(form, name):
    """The field payload; multiple selects carry their list of selected values."""
    field = form.fields[name]
    if isinstance(field.widget, forms.SelectMultiple):
        value = form[name].value() or []
        payload = {
            "name": name,
            "label": str(form[name].label),
            "required": field.required,
            "disabled": field.disabled,
            "widget": "selectmultiple",
            "help_text": str(field.help_text or ""),
            "value": [str(getattr(v, "pk", v)) for v in value],
            "attrs": {},
            "choices": [
                {"value": str(getattr(c, "value", c)), "label": str(label)}
                for c, label in field.choices
            ],
        }
    else:
        payload = _field(form, name)
    payload["html"] = {
        key: str(value)
        for key, value in field.widget.attrs.items()
        if key in ("class", "placeholder")
    }
    return payload


def _form_payload(vista, form, request):
    centro = vista.centro if hasattr(vista, "centro") else vista.object.centro
    return {
        "centro": {"id": centro.pk, "nombre": centro.nombre, "tipo": centro.tipo},
        "fields": [_form_field(form, name) for name in form.fields],
        **_errors(form),
        "messages": pending_messages(request),
    }


def _answer(vista, respuesta, request):
    if respuesta.status_code != 302:
        return Response(
            _form_payload(vista, respuesta.context_data["form"], request), status=400
        )
    queued = peek_messages(request)
    return Response(
        {
            "url": respuesta["Location"],
            "message": queued[-1]["message"] if queued else "",
            "level": queued[-1]["level"] if queued else "info",
        }
    )


class ActividadCrearWebView(CdfWebView):
    """``/api/web/cdf/centros/<centro_id>/actividades/nueva/``: the form or the native save."""

    http_method_names = ["get", "post"]

    def _vista(self, request, centro_id):
        vista = native_view(ActividadCentroCreateView, request, centro_id=centro_id)
        django_request = request._request  # pylint: disable=protected-access
        return vista, vista.dispatch(django_request, centro_id=centro_id)

    def get(self, request, centro_id):
        vista, respuesta = self._vista(request, centro_id)
        return Response(_form_payload(vista, respuesta.context_data["form"], request))

    def post(self, request, centro_id):
        vista, respuesta = self._vista(request, centro_id)
        return _answer(vista, respuesta, request)


class ActividadEditarWebView(CdfWebView):
    """``/api/web/cdf/actividades/<pk>/editar/``: current values or the native save."""

    http_method_names = ["get", "post"]

    def _vista(self, request, pk):
        vista = native_view(ActividadCentroUpdateView, request, pk=pk)
        django_request = request._request  # pylint: disable=protected-access
        return vista, vista.dispatch(django_request, pk=pk)

    def get(self, request, pk):
        vista, respuesta = self._vista(request, pk)
        return Response(_form_payload(vista, respuesta.context_data["form"], request))

    def post(self, request, pk):
        vista, respuesta = self._vista(request, pk)
        return _answer(vista, respuesta, request)
