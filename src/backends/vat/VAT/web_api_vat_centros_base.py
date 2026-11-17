"""Shared bases of the V06.01 web API (centros, contactos, identificadores, ubicaciones, modalidades).

Each endpoint runs the native view (``setup`` + ``get_form`` / ``form_valid`` / ``post``) and projects
its result. A valid POST answers ``{"ok": true, "redirect": <native success url>}``; an invalid one
answers 400 with the bound form (fields, errors and non-field errors), so a rejected write leaves
the stored data unchanged.
"""

import copy
import json

from django.http import Http404, JsonResponse
from django.urls import reverse
from rest_framework.exceptions import NotFound
from rest_framework.response import Response

from VAT.web_api_common import VatNativeReadView, campo_formulario


def redireccion(respuesta):
    """Success url of a native redirect (or of the native modal JSON answer)."""
    destino = respuesta.headers.get("Location")
    if destino is None:
        destino = json.loads(respuesta.content)["redirect_url"]
    return Response({"ok": True, "redirect": destino})


def con_mensaje(respuesta, vista, form):
    """Add to a rejected answer the ``message`` the native view sends its modal script (its AJAX ``form_invalid``), if it sends one."""
    original = vista.request
    ajax = copy.copy(original)
    ajax.META = {**original.META, "HTTP_X_REQUESTED_WITH": "XMLHttpRequest"}
    ajax.__dict__.pop(
        "headers", None
    )  # the native check reads the cached ``request.headers``
    vista.request = ajax
    try:
        nativa = vista.form_invalid(form)
    finally:
        vista.request = original
    if isinstance(nativa, JsonResponse):
        mensaje = json.loads(nativa.content).get("message")
        if isinstance(mensaje, str):
            respuesta.data["message"] = mensaje
    return respuesta


class VatEscrituraWebView(VatNativeReadView):
    """GET/POST of a native create, update or delete view."""

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


class VatFormWebView(VatEscrituraWebView):
    """Create (``crear = True``) or update form of a native ``ModelForm`` view."""

    crear = False
    lista_name = ""

    def objeto(self, vista):
        return None if self.crear else vista.get_object()

    def extra(self, vista, form):  # pylint: disable=unused-argument
        return {}

    def formulario(self, vista, form, status=200):
        return Response(
            {
                "editing": form.instance.pk is not None,
                "fields": [campo_formulario(form[nombre]) for nombre in form.fields],
                "non_field_errors": [str(e) for e in form.non_field_errors()],
                "urls": {"list": reverse(self.lista_name)},
                **self.extra(vista, form),
            },
            status=status,
        )

    def get(self, request, **kwargs):
        vista = self.preparar(kwargs)
        return self.formulario(vista, vista.get_form())

    def post(self, request, **kwargs):
        vista = self.preparar(kwargs)
        form = vista.get_form()
        if form.is_valid():
            return redireccion(vista.form_valid(form))
        return con_mensaje(self.formulario(vista, form, status=400), vista, form)


class VatBajaWebView(VatEscrituraWebView):
    """Confirmation summary (GET) and native deletion (POST) of a ``DeleteView``."""

    def resumen(self, objeto):
        raise NotImplementedError

    def get(self, request, **kwargs):
        return Response(self.resumen(self.preparar(kwargs).object))

    def post(self, request, **kwargs):
        vista = self.preparar(kwargs)
        return redireccion(
            vista.post(request._request, **kwargs)  # pylint: disable=protected-access
        )
