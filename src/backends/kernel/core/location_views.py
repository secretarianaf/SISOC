"""Previsualización de un domicilio público, sin leer ni modificar legajos."""

from django import forms
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.views import View

from core.services.geolocation import locate_address


class AddressPreviewForm(forms.Form):
    provincia = forms.CharField(max_length=255)
    municipio = forms.CharField(max_length=255, required=False)
    localidad = forms.CharField(max_length=255, required=False)
    calle = forms.CharField(max_length=255, required=False)
    numero = forms.CharField(max_length=50, required=False)
    altura = forms.CharField(max_length=50, required=False)
    domicilio = forms.CharField(max_length=500, required=False)

    def clean(self):
        data = super().clean()
        address = data.get("domicilio")
        if not address:
            number = data.get("numero") or data.get("altura")
            if not data.get("calle") or not number:
                raise forms.ValidationError("Complete calle y altura o un domicilio.")
            address = f'{data["calle"]} {number}'
        data["address"] = address
        return data


class AddressPreviewView(LoginRequiredMixin, View):
    """Geocodifica texto del formulario para cualquier usuario autenticado.

    No autoriza edición: cada módulo valida su guardado con los permisos propios.
    """

    def post(self, request):
        form = AddressPreviewForm(request.POST)
        if not form.is_valid():
            result, status = {"status": "invalid", "errors": form.errors}, 400
        else:
            data = form.cleaned_data
            result = locate_address(
                address=data["address"],
                province=data["provincia"],
                locality=data["localidad"],
                municipality=data["municipio"],
            )
            status = 503 if result["status"] == "unavailable" else 200
        response = JsonResponse(result, status=status)
        response["Cache-Control"] = "private, no-store"
        return response
