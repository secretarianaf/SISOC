"""Web API (G1 v1) of the comedor nómina soft-delete confirmations (CO01 «Dar de baja»).

``/api/web/comedores/comedores/<pk>/admision/<admision_pk>/nomina/<pk2>/eliminar/``
and ``/api/web/comedores/comedores/<pk>/nomina/<pk2>/eliminar/`` run
``NominaDeleteView`` and ``NominaDirectaDeleteView`` themselves: GET projects the
confirmation page (``comedor/nomina_confirm_delete.html`` over
``components/delete_confirm.html``) and POST runs the native ``post()`` (scoped lookup,
soft delete with the user, native message, redirect to the nómina). The routes keep the
native permission, ``permissions_any_required(["comedores.delete_nomina"])``.

Native quirk kept: the breadcrumb links ``comedor_detalle`` with the nómina id.
"""

from django.http import Http404
from django.urls import reverse
from rest_framework.exceptions import NotFound
from rest_framework.response import Response

from comedores.views.nomina import NominaDeleteView, NominaDirectaDeleteView
from core.web_gate import WebGatePermission
from intervenciones.web_api import NativeWebView, requires_any
from intervenciones.web_api_baja import confirmacion

BAJA_NOMINA = ["comedores.delete_nomina"]


class _NominaBajaWebView(NativeWebView):
    permission_classes = [WebGatePermission, requires_any(BAJA_NOMINA)]
    http_method_names = ["get", "post", "head"]
    native_view = None

    def _vista(self, request, **kwargs):
        vista = self.native(self.native_view, request, **kwargs)
        try:
            vista.object = vista.get_object()
        except Http404 as exc:
            raise NotFound() from exc
        return vista

    def _get(self, request, cancel_url, **kwargs):
        vista = self._vista(request, **kwargs)
        contexto = vista.get_context_data()
        objeto = contexto["object"]
        return Response(
            {
                **confirmacion(contexto, cancel_url, request),
                "breadcrumb": {
                    "etiqueta": str(objeto),
                    "url": reverse("comedor_detalle", args=[objeto.id]),
                },
            }
        )

    def _post(self, request, **kwargs):
        vista = self._vista(request, **kwargs)
        # pylint: disable-next=protected-access
        respuesta = vista.post(request._request)
        return Response({"ok": True, "redirect": respuesta["Location"]})


class NominaBajaAdmisionWebView(_NominaBajaWebView):
    """``…/comedores/<pk>/admision/<admision_pk>/nomina/<pk2>/eliminar/``."""

    native_view = NominaDeleteView

    def get(self, request, pk, admision_pk, pk2):
        return self._get(
            request,
            reverse("nomina_ver", args=[pk, admision_pk]),
            pk=pk,
            admision_pk=admision_pk,
            pk2=pk2,
        )

    def post(self, request, pk, admision_pk, pk2):
        return self._post(request, pk=pk, admision_pk=admision_pk, pk2=pk2)


class NominaBajaDirectaWebView(_NominaBajaWebView):
    """``…/comedores/<pk>/nomina/<pk2>/eliminar/``."""

    native_view = NominaDirectaDeleteView

    def get(self, request, pk, pk2):
        return self._get(
            request, reverse("nomina_directa_ver", args=[pk]), pk=pk, pk2=pk2
        )

    def post(self, request, pk, pk2):
        return self._post(request, pk=pk, pk2=pk2)
