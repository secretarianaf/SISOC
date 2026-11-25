"""Web API (G1 v1) of the comedor card holder (CO07.03).

``GET`` and ``POST`` ``/api/web/comedores/comedores/<pk>/responsable-tarjeta/`` run
the native ``ResponsableTarjetaComedorUpdateView`` itself: the object scope of
``get_scoped_comedor_queryset``, the "Alimentar Comunidad" program rule and the
exact membership of the ``Tecnico Comedor`` group (a user whose permission passes
the route but who lacks the group gets the native 404; no new superuser bypass),
and ``ResponsableTarjetaComedorForm`` with its Provincia > Municipio > Localidad
chain, its relation checks and the save of only its nine fields. React gets the
real form's fields in template order, the option lists the form built for the
current values and the errors; it never rebuilds a rule. After the web gate the
native route guard applies unchanged:
``permissions_any_required(["auth.role_tecnico_comedor"])``.

A valid save answers the ficha redirect without a custom message. This endpoint
is not coupled to the main comedor form: only the nine ``responsable_tarjeta_*``
fields exist here, and no file or email is involved.
"""

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
from comedores.views.comedor import ResponsableTarjetaComedorUpdateView

TARJETA_PERMISSIONS = ["auth.role_tecnico_comedor"]
# ``responsable_tarjeta_form.html`` renders exactly these controls, in this order.
FIELDS = (
    "responsable_tarjeta_nombre",
    "responsable_tarjeta_mail",
    "responsable_tarjeta_dni",
    "responsable_tarjeta_cuit",
    "responsable_tarjeta_telefono",
    "responsable_tarjeta_domicilio",
    "responsable_tarjeta_provincia",
    "responsable_tarjeta_municipio",
    "responsable_tarjeta_localidad",
)
ATTRS = ("maxlength", "minlength")


class GestionarTarjeta(BasePermission):
    def has_permission(self, request, view):
        return _has_any_permissions(request.user, TARJETA_PERMISSIONS)


def _valor(bound):
    value = bound.value()
    if value is None:
        return ""
    return str(value)


def _opciones(bound):
    choices = getattr(bound.field, "choices", None)
    if choices is None:
        return None
    return [{"value": str(v), "label": str(label)} for v, label in choices]


def _campo(bound):
    field = bound.field
    widget = field.widget
    opciones = _opciones(bound)
    return {
        "name": bound.html_name,
        "label": str(bound.label or ""),
        "type": "select" if opciones is not None else widget.input_type or "text",
        "required": field.required,
        "help": str(field.help_text or ""),
        "value": _valor(bound),
        "options": opciones,
        "errors": [str(e) for e in bound.errors],
        "attrs": {
            k: str(v)
            for k, v in {**field.widget_attrs(widget), **widget.attrs}.items()
            if k in ATTRS
        },
    }


def _tarjeta(context):
    form = context["form"]
    pk = context["object"].pk
    return {
        "comedor_id": pk,
        "fields": [_campo(form[name]) for name in FIELDS],
        "non_field_errors": [str(e) for e in form.non_field_errors()],
        "urls": {
            "ficha": reverse("comedor_detalle", kwargs={"pk": pk}),
            "municipios": reverse("ajax_load_municipios"),
            "localidades": reverse("ajax_load_localidades"),
        },
    }


class ComedorTarjetaWebView(APIView):
    """The native card-holder view: ``GET`` projects its form, ``POST`` saves it."""

    authentication_classes = [SessionAuthentication]
    permission_classes = [WebGatePermission, GestionarTarjeta]
    renderer_classes = [JSONRenderer]
    http_method_names = ["get", "head", "post"]

    @staticmethod
    def _native(request, pk):
        django_request = request._request  # pylint: disable=protected-access
        vista = ResponsableTarjetaComedorUpdateView()
        vista.setup(django_request, pk=pk)
        return vista.dispatch(django_request, pk=pk)

    def get(self, request, pk):
        respuesta = self._native(request, pk)
        return Response({"form": _tarjeta(respuesta.context_data)})

    def post(self, request, pk):
        respuesta = self._native(request, pk)
        if not hasattr(respuesta, "context_data"):
            return Response({"redirect": respuesta.url})
        form = respuesta.context_data["form"]
        return Response(
            {
                "errors": {
                    nombre: [str(e) for e in errores]
                    for nombre, errores in form.errors.items()
                    if nombre != "__all__"
                },
                "non_field_errors": [str(e) for e in form.non_field_errors()],
                "form": _tarjeta(respuesta.context_data),
            },
            status=status.HTTP_400_BAD_REQUEST,
        )
