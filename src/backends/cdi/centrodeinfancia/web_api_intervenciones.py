"""Web API (G1 v1) of the CDI intervention detail and its attached document (CDI06, CDI-F2).

Session transport over the native views. Order of checks, as in
``web_api_observaciones``:

1. G1 (``WebGatePermission``): 401/403 JSON, or the signed attestation in the
   runtime.
2. The same permission code as the URL decorator in ``centrodeinfancia/urls.py``.
3. The native view or function, with its own scope (``_intervenciones_cdi_queryset_scoped``).

Download contract (CDI-F2, per object): the intervention is resolved by primary
key inside the actor's scope; the server reads ``FieldFile.name`` and the
storage of that object, never a path or a name sent by the client; the bytes
are served as an attachment with a controlled name and ``private, no-store``
plus ``nosniff``. A missing intervention, one outside the scope, a soft-deleted
one, one without attachment or a missing file all answer the same 404. This
endpoint does not close the legacy ``/media/documentacion/`` alias; that closure
is a separate decision of the CDI-F2 contract.
"""

import os

from django.core.exceptions import PermissionDenied
from django.http import FileResponse, Http404, JsonResponse
from django.template.defaultfilters import date as date_filter
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_protect

from centrodeinfancia.views import (
    IntervencionCentroInfanciaDetailView,
    eliminar_archivo_intervencion_centrodeinfancia,
)
from centrodeinfancia.web_api import pending_messages
from centrodeinfancia.web_api_observaciones import (
    NO_ENCONTRADA,
    PERMISO_BAJA,
    PERMISO_VER,
    SIN_PERMISO,
    _centro,
    _gate,
    _json,
    _ObservacionTransportMixin,
    _privada,
)
from core.decorators import permissions_any_required


def _documentacion(intervencion, usuario):
    campo = intervencion.documentacion
    if not campo:
        return None
    return {
        "name": campo.name,
        "descargar": reverse(
            "centrodeinfancia_web_intervencion_documentacion",
            args=[intervencion.pk],
        ),
        # The native template draws the delete button for superusers only.
        "eliminar": (
            reverse(
                "centrodeinfancia_web_intervencion_documentacion_eliminar",
                args=[intervencion.pk],
            )
            if usuario.is_superuser
            else None
        ),
    }


class IntervencionDetalleWebView(
    _ObservacionTransportMixin, IntervencionCentroInfanciaDetailView
):
    """``GET /api/web/cdi/intervenciones/<pk>/``: the native detail card."""

    permission_code = PERMISO_VER
    http_method_names = ["get", "head"]

    def render_to_response(self, context, **response_kwargs):
        intervencion = context["intervencion"]
        # Each value is what ``{{ ... }}`` prints in intervencion_detail_view.html.
        return JsonResponse(
            {
                "id": intervencion.pk,
                "centro": _centro(context["centro"]["id"], context["centro"]["nombre"]),
                "fecha": date_filter(
                    timezone.localtime(intervencion.fecha), "d/m/Y H:i"
                ),
                "tipo_intervencion": str(intervencion.tipo_intervencion),
                "subintervencion": str(intervencion.subintervencion),
                "destinatario": str(intervencion.destinatario),
                "forma_contacto": str(intervencion.forma_contacto),
                "observaciones": str(intervencion.observaciones),
                "documentacion": _documentacion(intervencion, self.request.user),
                "messages": pending_messages(self.request),
            }
        )


class IntervencionDocumentacionWebView(
    _ObservacionTransportMixin, IntervencionCentroInfanciaDetailView
):
    """``GET /api/web/cdi/intervenciones/<pk>/documentacion/``: authenticated download."""

    permission_code = PERMISO_VER
    http_method_names = ["get", "head"]

    def render_to_response(self, context, **response_kwargs):
        campo = context["intervencion"].documentacion
        if not campo:
            raise Http404
        try:
            archivo = campo.open("rb")
        except (OSError, ValueError) as exc:
            raise Http404 from exc
        respuesta = FileResponse(
            archivo, as_attachment=True, filename=os.path.basename(campo.name)
        )
        respuesta["X-Content-Type-Options"] = "nosniff"
        return respuesta


@csrf_protect
def intervencion_documentacion_eliminar_web(request, intervencion_id):
    """``POST /api/web/cdi/intervenciones/<pk>/documentacion/eliminar/``: native delete."""
    response = _gate(request)
    if response is not None:
        return response
    if request.method != "POST":
        return _json({"detail": "Método no permitido."}, 405)
    guarded = permissions_any_required([PERMISO_BAJA])(
        eliminar_archivo_intervencion_centrodeinfancia
    )
    try:
        response = guarded(request, intervencion_id=intervencion_id)
    except PermissionDenied as exc:
        return _json({"detail": str(exc) or SIN_PERMISO}, 403)
    except Http404:
        return _json({"detail": NO_ENCONTRADA}, 404)
    if response.status_code == 302:
        convertida = JsonResponse({"ok": True, "redirect": response["Location"]})
        convertida.cookies = response.cookies
        response = convertida
    return _privada(response)
