"""Backoffice: anular un acta y marcarla como de prueba (sólo POST).

Acceso: ``puede_gestionar_inspecciones`` (coordinación, permiso
``inspecciones.gestionar_inspecciones`` o superusuario). La regla de negocio
vive en ``inspecciones.services.anulacion``.
"""

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect
from django.urls import NoReverseMatch, reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views import View

from inspecciones.access import puede_gestionar
from inspecciones.models import Acta
from inspecciones.services.anulacion import anular_acta, marcar_prueba

VALORES_PRUEBA = {"1": True, "0": False}


class _AccionActaView(LoginRequiredMixin, UserPassesTestMixin, View):
    # Sin sesión: al login. Con sesión y sin permiso: 403.
    http_method_names = ["post"]

    def test_func(self):
        return puede_gestionar(self.request.user)

    def post(self, request, numero):
        acta = get_object_or_404(Acta, numero=numero)
        try:
            mensaje = self.ejecutar(acta)
        except ValidationError as exc:
            messages.error(request, " ".join(exc.messages))
        else:
            messages.success(request, mensaje)
        return redirect(self._destino(numero))

    def ejecutar(self, acta):
        raise NotImplementedError

    def _destino(self, numero):
        siguiente = self.request.POST.get("next", "")
        if siguiente and url_has_allowed_host_and_scheme(
            siguiente,
            allowed_hosts={self.request.get_host()},
            require_https=self.request.is_secure(),
        ):
            return siguiente
        try:
            return reverse("inspecciones_acta_detalle", args=[numero])
        except NoReverseMatch:
            return reverse("inspecciones_panel")


class AnularActaView(_AccionActaView):
    def ejecutar(self, acta):
        anular_acta(acta, self.request.POST.get("motivo", ""), self.request.user)
        return f"Acta {acta.numero} anulada."


class MarcarPruebaActaView(_AccionActaView):
    def ejecutar(self, acta):
        valor = VALORES_PRUEBA.get(self.request.POST.get("es_prueba", ""))
        if valor is None:
            raise ValidationError("Valor de prueba inválido.")
        marcar_prueba(acta, valor, self.request.user)
        if valor:
            return f"Acta {acta.numero} marcada como de prueba."
        return f"Acta {acta.numero} desmarcada como de prueba."
