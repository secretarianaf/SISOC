"""Web API (G1 v1) of the template version editor (AD01.02, ``version_form.html``).

``GET /api/web/comedores/admisiones/plantillas-informe/<pk>/versiones/<version_pk>/``
returns what the native ``PlantillaInformeTecnicoVersionUpdateView`` renders and
``POST`` runs its native ``post()``: ``PlantillaInformeTecnicoVersionForm`` (the
only HTML sanitising, ``sanitizar_contenido_template``), ``guardar_borrador`` and
its message. A 302 becomes ``{"ok": true, "redirect": ...}``; a rejected form
(including the service refusing the save) returns 400 with the bound payload.
Only the drafts of that template are editable: any other version is a 404 on
GET and POST, as on the native page. Access is the native guard (see
``admisiones.web_api_templates``) plus the session CSRF check of every web POST.
"""

from django.http import Http404
from django.urls import reverse
from rest_framework.exceptions import NotFound
from rest_framework.response import Response

from admisiones.views.templates_informe_tecnico import (
    PlantillaInformeTecnicoVersionUpdateView,
)
from admisiones.web_api_template_crear import CONTENT_TYPES
from admisiones.web_api_templates import (
    GestorTemplatesWebView,
    _navigation,
    pending_messages,
)


def _campo(form, nombre):
    bound = form[nombre]
    campo = form.fields[nombre]
    value = bound.value()
    return {
        "label": str(campo.label),
        "value": "" if value is None else str(value),
        "errors": [str(error) for error in bound.errors],
        "placeholder": campo.widget.attrs.get("placeholder", ""),
    }


def _payload(vista, form, request):
    version = vista.object
    plantilla = version.plantilla
    return {
        "version": {"id": version.pk, "numero": version.numero},
        "plantilla": {
            "id": plantilla.pk,
            "codigo": plantilla.codigo,
            "nombre": plantilla.nombre,
        },
        "contenido_html": _campo(form, "contenido_html"),
        "observaciones": _campo(form, "observaciones"),
        "non_field_errors": [str(error) for error in form.non_field_errors()],
        "variables": [
            {
                "categoria": variable.categoria,
                "nombre": variable.nombre,
                "codigo": variable.codigo,
                "token": variable.token,
            }
            for variable in vista.get_context_data(form=form)["variables_template"]
        ],
        "urls": {
            **_navigation(),
            "detalle": reverse("gestor_templates_detalle", args=[plantilla.pk]),
            "previsualizar": reverse(
                "gestor_templates_version_previsualizar",
                args=[plantilla.pk, version.pk],
            ),
        },
        "messages": pending_messages(request),
    }


class VersionEditarWebView(GestorTemplatesWebView):
    """``/api/web/comedores/admisiones/plantillas-informe/<pk>/versiones/<version_pk>/``."""

    http_method_names = ["get", "head", "post"]

    def _view(self, request, pk, version_pk):
        vista = PlantillaInformeTecnicoVersionUpdateView()
        # pylint: disable-next=protected-access
        vista.setup(request._request, plantilla_pk=pk, version_pk=version_pk)
        try:
            vista.object = vista.get_object()
        except Http404 as exc:
            raise NotFound() from exc
        return vista

    def get(self, request, pk, version_pk):
        vista = self._view(request, pk, version_pk)
        return Response(_payload(vista, vista.get_form(), request))

    def post(self, request, pk, version_pk):
        # pylint: disable-next=protected-access
        if request._request.content_type not in CONTENT_TYPES:
            return Response({"detail": "Formato de solicitud no admitido."}, status=415)
        vista = self._view(request, pk, version_pk)
        respuesta = vista.post(request._request)  # pylint: disable=protected-access
        if respuesta.status_code == 302:
            return Response({"ok": True, "redirect": respuesta["Location"]})
        form = respuesta.context_data["form"]
        return Response(_payload(vista, form, request), status=400)
