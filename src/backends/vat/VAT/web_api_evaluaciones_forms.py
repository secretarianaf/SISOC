"""Web API (G1 v1) del alta, edición y baja de evaluaciones de VAT (V08.02).

``/api/web/vat/evaluaciones/nueva/``, ``<pk>/editar/`` y ``<pk>/eliminar/`` corren las
vistas nativas (``EvaluacionCreateView``, ``EvaluacionUpdateView``,
``EvaluacionDeleteView``): su formulario, ``form_valid`` (mensaje y guardado) y la baja
física. El POST responde ``{"ok": true, "redirect": <url>}`` o, con el formulario
inválido, 400 con los campos y errores. Acceso: ``VAT.add/change/delete_evaluacion``.
"""

from django.http import Http404
from django.urls import reverse
from rest_framework.exceptions import NotFound
from rest_framework.response import Response

from VAT.views.evaluacion import (
    EvaluacionCreateView,
    EvaluacionDeleteView,
    EvaluacionUpdateView,
)
from VAT.web_api_common import VatNativeReadView, campo_formulario


class _EvaluacionEscrituraView(VatNativeReadView):
    http_method_names = ["get", "head", "post"]

    def preparar(self, kwargs):
        vista = self.native(**kwargs)
        try:
            vista.object = self.objeto(vista)
        except Http404 as exc:
            raise NotFound() from exc
        return vista

    def objeto(self, vista):
        return vista.get_object()

    @staticmethod
    def redireccion(respuesta):
        return Response({"ok": True, "redirect": respuesta["Location"]})


class _EvaluacionFormView(_EvaluacionEscrituraView):
    def get(self, request, **kwargs):
        vista = self.preparar(kwargs)
        return self.formulario(vista.get_form())

    def post(self, request, **kwargs):
        vista = self.preparar(kwargs)
        form = vista.get_form()
        if form.is_valid():
            return self.redireccion(vista.form_valid(form))
        return self.formulario(form, status=400)

    @staticmethod
    def formulario(form, status=200):
        return Response(
            {
                "editing": form.instance.pk is not None,
                "fields": [campo_formulario(form[nombre]) for nombre in form.fields],
                "urls": {"list": reverse("vat_evaluacion_list")},
            },
            status=status,
        )


class EvaluacionCreateWebView(_EvaluacionFormView):
    """``GET|POST .../evaluaciones/nueva/``."""

    native_class = EvaluacionCreateView
    codigos = ["VAT.add_evaluacion"]

    def objeto(self, vista):
        return None


class EvaluacionUpdateWebView(_EvaluacionFormView):
    """``GET|POST .../evaluaciones/<pk>/editar/``."""

    native_class = EvaluacionUpdateView
    codigos = ["VAT.change_evaluacion"]


class EvaluacionDeleteWebView(_EvaluacionEscrituraView):
    """``GET|POST .../evaluaciones/<pk>/eliminar/``: confirmación y baja física nativa."""

    native_class = EvaluacionDeleteView
    codigos = ["VAT.delete_evaluacion"]

    def get(self, request, **kwargs):
        e = self.preparar(kwargs).object
        return Response(
            {
                "nombre": e.nombre,
                "tipo_label": e.get_tipo_display(),
                "comision": e.comision.codigo_comision,
                "urls": {"detail": reverse("vat_evaluacion_detail", args=[e.pk])},
            }
        )

    def post(self, request, **kwargs):
        vista = self.preparar(kwargs)
        return self.redireccion(vista.form_valid(vista.get_form()))
