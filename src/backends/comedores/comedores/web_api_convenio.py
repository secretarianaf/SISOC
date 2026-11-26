"""Web API (G1 v1) of the comedor PNUD/Abordaje convenio (CO07.03).

``GET`` and ``POST`` ``/api/web/comedores/comedores/<pk>/convenio-pnud/`` run the
native ``ComedorDatosConvenioPnudUpdateView`` itself: its ``dispatch`` (object
scope, the "only PNUD or Abordaje Comunitario" refusal with its flash message and
redirect), the ``get_or_create`` of the one-to-one record, the variant form
(``ComedorDatosConvenioPnudForm``) with its Decimal monto fields and the
preservation of historical cents, and the atomic ``form_valid`` save. React gets
the real form's fields (name, label, value as the widget renders it, errors), the
read-only prefill and the variant flags; it never rebuilds a rule. After the web
gate the native route guard applies unchanged:
``permissions_any_required(["comedores.change_comedor"])``.

Known source behaviours kept as they are: the native ``GET`` creates the empty
record when it does not exist (not a pure read), a valid save redirects to the
ficha without a custom success message and the form fields removed by the
variant are neither sent nor cleaned (their stored values stay).
"""

from django.http import HttpResponseRedirect
from django.urls import reverse
from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import BasePermission
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.views import APIView

# The exact predicate of the native URL decorator.
from core.decorators import _has_any_permissions
from core.web_gate import WebGatePermission
from comedores.forms.convenio_pnud_form import MontoConvenioField
from comedores.views.comedor import ComedorDatosConvenioPnudUpdateView
from comedores.web_api_comedores import pending_messages

EDIT_PERMISSIONS = ["comedores.change_comedor"]
PREFILL_KEYS = (
    "organizacion_solicitante",
    "codigo_proyecto",
    "estado_general",
    "subestado",
    "nombre_espacio",
    "id_externo",
    "domicilio_completo",
)
ATTRS = ("maxlength", "minlength", "min", "max", "step", "inputmode")


class EditarComedor(BasePermission):
    def has_permission(self, request, view):
        return _has_any_permissions(request.user, EDIT_PERMISSIONS)


def _valor(bound):
    """The value as the native widget renders it (``1.000`` for a monto, ``""`` for none)."""
    value = bound.field.widget.format_value(bound.value())
    return "" if value is None else str(value)


def _campo(bound):
    field = bound.field
    widget = field.widget
    return {
        "name": bound.html_name,
        "label": str(bound.label or ""),
        "type": widget.input_type or "text",
        "required": field.required,
        "help": str(field.help_text or ""),
        "value": _valor(bound),
        "monto": isinstance(field, MontoConvenioField),
        "errors": [str(e) for e in bound.errors],
        "attrs": {
            k: str(v)
            for k, v in {**field.widget_attrs(widget), **widget.attrs}.items()
            if k in ATTRS
        },
    }


def _convenio(context):
    form = context["form"]
    comedor = context["comedor"]
    return {
        "comedor_id": comedor.pk,
        "prefill": {key: str(context["prefill_data"][key]) for key in PREFILL_KEYS},
        "territoriales": [
            {"territorial": str(t["territorial"]), "codigo": str(t["codigo"])}
            for t in context["territoriales_por_proyecto"]
        ],
        "es_linea_secos": bool(context["es_linea_secos"]),
        "es_linea_tradicional": bool(context["es_linea_tradicional"]),
        "fields": [_campo(form[name]) for name in form.fields],
        "non_field_errors": [str(e) for e in form.non_field_errors()],
        "urls": {"ficha": reverse("comedor_detalle", kwargs={"pk": comedor.pk})},
    }


class ComedorConvenioWebView(APIView):
    """The native convenio view: ``GET`` projects its form, ``POST`` saves it."""

    authentication_classes = [SessionAuthentication]
    permission_classes = [WebGatePermission, EditarComedor]
    renderer_classes = [JSONRenderer]
    http_method_names = ["get", "head", "post"]

    def _native(self, request, pk):
        django_request = request._request  # pylint: disable=protected-access
        vista = ComedorDatosConvenioPnudUpdateView()
        vista.setup(django_request, pk=pk)
        return vista.dispatch(django_request, pk=pk)

    @staticmethod
    def _redirect(respuesta):
        return Response({"redirect": respuesta.url})

    def get(self, request, pk):
        respuesta = self._native(request, pk)
        if isinstance(respuesta, HttpResponseRedirect):
            return self._redirect(respuesta)
        return Response(
            {
                "form": _convenio(respuesta.context_data),
                "messages": pending_messages(request),
            }
        )

    def post(self, request, pk):
        respuesta = self._native(request, pk)
        if isinstance(respuesta, HttpResponseRedirect):
            return self._redirect(respuesta)
        form = respuesta.context_data["form"]
        return Response(
            {
                "errors": {
                    nombre: [str(e) for e in errores]
                    for nombre, errores in form.errors.items()
                    if nombre != "__all__"
                },
                "non_field_errors": [str(e) for e in form.non_field_errors()],
                "form": _convenio(respuesta.context_data),
            },
            status=status.HTTP_400_BAD_REQUEST,
        )
