"""Web API (G1 v1) of the template create form (AD01.02, ``form.html``).

``GET /api/web/comedores/admisiones/plantillas-informe/crear/`` returns what the
native ``PlantillaInformeTecnicoCreateView`` form renders; ``POST`` runs the
native ``post()`` (``PlantillaInformeTecnicoForm``, ``crear_plantilla`` and its
success message). A 302 becomes ``{"ok": true, "redirect": ...}`` and the next
GET consumes the queued message; a rejected form returns 400 with the bound
payload. Access is the native guard (see ``admisiones.web_api_templates``) plus
the session CSRF check of every web POST. A residual ``ValidationError`` of
``crear_plantilla`` is a 500, as on the native page.
"""

from django.urls import reverse
from rest_framework.response import Response

from admisiones.views.templates_informe_tecnico import (
    PlantillaInformeTecnicoCreateView,
)
from admisiones.web_api_templates import (
    GestorTemplatesWebView,
    _navigation,
    pending_messages,
)

FIELDS = (
    "nombre",
    "descripcion",
    "tipo_admision",
    "tipo_convenio",
    "es_ex_pnud",
    "estado_convenio_pnud",
    "tipo_renovacion",
    "estado_financiamiento",
    "informe_complementario_modifica_prestaciones",
)
CONTENT_TYPES = ("multipart/form-data", "application/x-www-form-urlencoded")


def _field(form, name):
    bound = form[name]
    field = form.fields[name]
    value = bound.value()
    payload = {
        "name": name,
        "required": bool(field.required and form.use_required_attribute),
        "value": "" if value is None else str(value),
    }
    if hasattr(field, "choices"):
        payload["choices"] = [
            {"value": "" if valor is None else str(valor), "label": str(etiqueta)}
            for valor, etiqueta in field.choices
        ]
    if getattr(field, "max_length", None):
        payload["max_length"] = field.max_length
    return payload


def _errors(form):
    return {
        name: [error["message"] for error in errores]
        for name, errores in form.errors.get_json_data().items()
        if name != "__all__"
    }


def _payload(form, request):
    return {
        "fields": [_field(form, name) for name in FIELDS],
        "errors": _errors(form),
        "non_field_errors": [str(error) for error in form.non_field_errors()],
        "urls": {**_navigation(), "cancelar": reverse("gestor_templates_listar")},
        "messages": pending_messages(request),
    }


class PlantillaCrearWebView(GestorTemplatesWebView):
    """``/api/web/comedores/admisiones/plantillas-informe/crear/``."""

    http_method_names = ["get", "head", "post"]

    def _view(self, request):
        vista = PlantillaInformeTecnicoCreateView()
        vista.setup(request._request)  # pylint: disable=protected-access
        vista.object = None
        return vista

    def get(self, request):
        return Response(_payload(self._view(request).get_form(), request))

    def post(self, request):
        # pylint: disable-next=protected-access
        if request._request.content_type not in CONTENT_TYPES:
            return Response({"detail": "Formato de solicitud no admitido."}, status=415)
        vista = self._view(request)
        respuesta = vista.post(request._request)  # pylint: disable=protected-access
        if respuesta.status_code == 302:
            return Response({"ok": True, "redirect": respuesta["Location"]})
        return Response(_payload(respuesta.context_data["form"], request), status=400)
