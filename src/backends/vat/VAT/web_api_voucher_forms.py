"""Web API (G1 v1) de los formularios de alta de vouchers y parametrías de VAT (V01.02).

``/api/web/vat/vouchers/asignar/``, ``asignar-masivo/`` y ``parametrias/nueva/`` corren
las vistas nativas ``VoucherCreateView``, ``VoucherAsignacionMasivaView`` y
``VoucherParametriaCreateView``: su formulario, su ``form_valid`` (servicio, mensaje y
guardado) y el recorrido masivo. El POST responde ``{"ok": true, "redirect": <url>}``
(alta y parametría), 200 con el resultado masivo, o 400 con los campos y errores del
formulario ligado. Acceso: ``VAT.add_voucher`` (la regla de las tres rutas nativas).
"""

from django.http import HttpResponse, HttpResponseRedirect
from django.urls import reverse
from rest_framework.response import Response

from VAT.views.voucher import VoucherAsignacionMasivaView, VoucherCreateView
from VAT.views.voucher_parametria import VoucherParametriaCreateView
from VAT.web_api_common import (
    VatNativeReadView,
    campo_formulario,
    mensajes_pendientes,
)

CODIGOS = ["VAT.add_voucher"]


def _formulario(form, request, extra=None, status=200):
    return Response(
        {
            "fields": [campo_formulario(form[nombre]) for nombre in form.fields],
            "urls": {"list": reverse("vat_voucher_list")},
            "messages": mensajes_pendientes(request),
            **(extra or {}),
        },
        status=status,
    )


class _AltaView(VatNativeReadView):
    """Alta con el ``CreateView`` nativo: ``form_valid`` decide la redirección."""

    http_method_names = ["get", "head", "post"]
    codigos = CODIGOS

    def preparar(self):
        vista = self.native()
        vista.object = None
        return vista

    def datos(self, vista, form):
        """``titulo`` del contexto nativo (``get_context_data``)."""
        return {"titulo": vista.get_context_data(form=form)["titulo"]}

    def get(self, request):
        vista = self.preparar()
        form = vista.get_form()
        return _formulario(form, vista.request, self.datos(vista, form))

    def post(self, request):
        vista = self.preparar()
        form = vista.get_form()
        respuesta = vista.form_valid(form) if form.is_valid() else None
        if isinstance(respuesta, HttpResponseRedirect):
            return Response({"ok": True, "redirect": respuesta["Location"]})
        return _formulario(form, vista.request, self.datos(vista, form), status=400)


class VoucherCreateWebView(_AltaView):
    """``GET|POST .../vouchers/asignar/``: ``voucher_form.html``."""

    native_class = VoucherCreateView


class ParametriaCreateWebView(_AltaView):
    """``GET|POST .../vouchers/parametrias/nueva/``: ``parametria_form.html``."""

    native_class = VoucherParametriaCreateView


class _AsignacionMasiva(VoucherAsignacionMasivaView):
    """La vista nativa con su render capturado: la API proyecta lo que la plantilla recibe."""

    capturado = None

    def _render(self, request, form, resultado=None):
        self.capturado = (form, resultado)
        return HttpResponse()


class VoucherMasivoWebView(VatNativeReadView):
    """``GET|POST .../vouchers/asignar-masivo/``: ``voucher_asignacion_masiva.html``."""

    http_method_names = ["get", "head", "post"]
    native_class = _AsignacionMasiva
    codigos = CODIGOS

    def _responder(self, vista):
        form, resultado = vista.capturado
        invalido = resultado is None and form.is_bound
        return _formulario(
            form,
            vista.request,
            {"resultado": resultado},
            status=400 if invalido else 200,
        )

    def get(self, request):
        vista = self.native()
        vista.get(vista.request)
        return self._responder(vista)

    def post(self, request):
        vista = self.native()
        vista.post(vista.request)
        return self._responder(vista)
