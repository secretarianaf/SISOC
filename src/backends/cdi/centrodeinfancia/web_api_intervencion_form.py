"""Web API (G1 v1) of the CDI intervention create and edit form (CDI06, ``intervencion_form.html``).

Session transport over the native views, as in ``web_api_observaciones``:

1. G1 (``WebGatePermission``): 401/403 JSON, or the signed attestation.
2. The same permission code as the URL decorator in ``centrodeinfancia/urls.py``.
3. The native view: ``IntervencionCentroInfanciaCreateView`` / ``...UpdateView`` with
   their form, fixed recipient, scope, author, messages and ``get_success_url``.

The template draws ``{{ form.as_p }}``, so the payload carries that exact markup
(``form_html``, without the CSRF token, which the page adds). The POST accepts
multipart (the attachment) or urlencoded, never JSON. A native redirect becomes
``{"ok": true, "redirect": ...}``; a rejected form answers 400 with the bound form.
Access is the native one: the create page does not check the centre scope on GET
(only when saving), and this API does not add a check.
"""

from django.http import JsonResponse
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie

from centrodeinfancia.views import (
    IntervencionCentroInfanciaCreateView,
    IntervencionCentroInfanciaUpdateView,
)
from centrodeinfancia.web_api import pending_messages
from centrodeinfancia.web_api_observaciones import (
    PERMISO_ALTA,
    PERMISO_EDICION,
    _ObservacionTransportMixin,
)

FORMATOS = ("multipart/form-data", "application/x-www-form-urlencoded")


class _FormularioTransportMixin(_ObservacionTransportMixin):
    def _native(self, request, *args, **kwargs):
        if request.method.lower() not in self.http_method_names:
            return self.http_method_not_allowed(request, *args, **kwargs)
        if request.method == "POST" and request.content_type not in FORMATOS:
            return JsonResponse(
                {"detail": "Formato de solicitud no admitido."}, status=415
            )
        # Skips the parent check (urlencoded only) and runs the native dispatch.
        return super(_ObservacionTransportMixin, self).dispatch(
            request, *args, **kwargs
        )

    def form_invalid(self, form):
        return self.render_to_response(self.get_context_data(form=form), status=400)

    def render_to_response(self, context, **response_kwargs):
        return JsonResponse(
            {
                "volver_url": reverse(
                    "centrodeinfancia_detalle", args=[self.kwargs["pk"]]
                ),
                "form_html": str(context["form"].as_p()),
                "messages": pending_messages(self.request),
            },
            status=response_kwargs.get("status", 200),
        )


@method_decorator(ensure_csrf_cookie, name="dispatch")
@method_decorator(csrf_protect, name="dispatch")
class IntervencionCrearWebView(
    _FormularioTransportMixin, IntervencionCentroInfanciaCreateView
):
    """``/api/web/cdi/centros/<pk>/intervenciones/crear/``: native create."""

    permission_code = PERMISO_ALTA


@method_decorator(ensure_csrf_cookie, name="dispatch")
@method_decorator(csrf_protect, name="dispatch")
class IntervencionEditarWebView(
    _FormularioTransportMixin, IntervencionCentroInfanciaUpdateView
):
    """``/api/web/cdi/centros/<pk>/intervenciones/<pk2>/editar/``: native edit."""

    permission_code = PERMISO_EDICION
