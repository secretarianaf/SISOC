"""Web API (G1 v1) of the CDI soft-delete confirmations: centre and nómina.

Same transport as ``centrodeinfancia.web_api_observaciones``: each API view
inherits the native delete view, so the scope, the CDI-A3 auditor veto, the
cascade preview, the soft delete, its message and the redirect stay the native
ones. Checks run in order: G1 gate, the URL permission of
``centrodeinfancia/urls.py``, then the native dispatch. GET projects
``components/delete_confirm.html`` with the values of each native template;
POST answers ``{"ok": true, "redirect": <Location>}``.
"""

from django.http import JsonResponse
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie

from centrodeinfancia.views import (
    CentroDeInfanciaDeleteView,
    NominaCentroInfanciaDeleteView,
)
from centrodeinfancia.web_api import pending_messages
from centrodeinfancia.web_api_observaciones import (
    _ObservacionTransportMixin,
    _preview,
)

PERMISO_BAJA_CENTRO = "centrodeinfancia.delete_centrodeinfancia"
PERMISO_BAJA_NOMINA = "centrodeinfancia.delete_nominacentroinfancia"


class _ConfirmacionMixin(_ObservacionTransportMixin):
    """The native confirmation context as JSON (``delete_confirm.html``)."""

    title = ""

    def cancel_url(self):
        raise NotImplementedError

    def render_to_response(self, context, **response_kwargs):
        preview = context.get("cascade_preview")
        return JsonResponse(
            {
                "id": self.object.pk,
                "title": self.title,
                "object_name": str(self.object).upper(),
                "cascade_preview": _preview(preview) if preview else None,
                "confirm_text": str(context["confirm_text"]),
                "cancel_text": str(context["cancel_text"]),
                "cancel_url": self.cancel_url(),
                "messages": pending_messages(self.request),
            },
            status=response_kwargs.get("status", 200),
        )


@method_decorator(ensure_csrf_cookie, name="dispatch")
@method_decorator(csrf_protect, name="dispatch")
class CentroEliminarWebView(_ConfirmacionMixin, CentroDeInfanciaDeleteView):
    """``/api/web/cdi/centros/<pk>/eliminar/``: native centre soft delete."""

    permission_code = PERMISO_BAJA_CENTRO
    title = "Eliminar Centro de Desarrollo Infantil"

    def cancel_url(self):
        return reverse("centrodeinfancia")


@method_decorator(ensure_csrf_cookie, name="dispatch")
@method_decorator(csrf_protect, name="dispatch")
class NominaEliminarWebView(_ConfirmacionMixin, NominaCentroInfanciaDeleteView):
    """``/api/web/cdi/centros/<pk>/nomina/<pk2>/eliminar/``: native nómina soft delete."""

    permission_code = PERMISO_BAJA_NOMINA
    title = "Eliminar registro de nómina"

    def cancel_url(self):
        return reverse("centrodeinfancia_nomina_ver", kwargs={"pk": self.kwargs["pk"]})
