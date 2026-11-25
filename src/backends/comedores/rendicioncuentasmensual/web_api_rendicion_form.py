"""Web API (G1 v1) of the monthly rendición form screens served by React (RM01.02).

``/api/web/comedores/rendicioncuentasmensual/`` keeps the permission of each native
URL (``rendicioncuentasmensual/urls.py``, superuser bypass included) and runs the
native view itself, so the form, its validation, the soft delete and the messages
stay the native ones:

* ``nuevo/<comedor_id>/``: ``RendicionCuentaMensualCreateView`` (``_form.html``).
* ``editar/<pk>/``: ``RendicionCuentaMensualUpdateView`` (``_datos_form.html``); its
  ``dispatch`` keeps the extra ``rendicioncuentasmensual.edit_rendicion_data`` check.
* ``eliminar/<pk>/``: ``RendicionCuentaMensualDeleteView`` (the shared
  ``components/delete_confirm.html``).

A native redirect becomes ``{"ok": true, "redirect": ...}``; a rejected form returns
400 with the page's form data.

An unknown comedor on a valid create POST is a native 500; it is a 404 here.
"""

from django.http import Http404
from django.urls import reverse
from django.utils.formats import localize
from rest_framework.exceptions import NotFound
from rest_framework.response import Response

from comedores.models import Comedor
from core.web_gate import WebGatePermission
from intervenciones.web_api import NativeWebView, pending_messages, requires_any
from intervenciones.web_api_baja import confirmacion
from rendicioncuentasmensual.urls import _RENDICION_PERM
from rendicioncuentasmensual.views import (
    RendicionCuentaMensualCreateView,
    RendicionCuentaMensualDeleteView,
    RendicionCuentaMensualUpdateView,
)

FORMATOS = ("multipart/form-data", "application/x-www-form-urlencoded")


def _valor(campo):
    """The value the widget renders (ISO for ``<input type="date">``), always text."""
    valor = campo.field.widget.format_value(campo.value())
    if isinstance(valor, (list, tuple)):
        valor = valor[0] if valor else ""
    return "" if valor is None else str(valor)


def _campo(form, nombre):
    campo = form[nombre]
    datos = {
        "name": nombre,
        "label": str(campo.label),
        "required": campo.field.required,
        "value": _valor(campo),
    }
    if hasattr(campo.field, "choices"):
        datos["choices"] = [
            {"value": str(valor), "label": str(etiqueta)}
            for valor, etiqueta in campo.field.choices
        ]
    maxlength = getattr(campo.field, "max_length", None)
    if maxlength:
        datos["maxlength"] = maxlength
    rows = campo.field.widget.attrs.get("rows")
    if rows:
        datos["rows"] = int(rows)
    return datos


def _errores(form):
    if not form.is_bound:
        return {}
    return form.errors.get_json_data()


class _FormularioWebView(NativeWebView):
    http_method_names = ["get", "post", "head"]
    permission_classes = [WebGatePermission, requires_any(_RENDICION_PERM)]

    def _vista(self, request, **kwargs):
        raise NotImplementedError

    def _datos(self, request, contexto, **kwargs):
        raise NotImplementedError

    def _responder(self, request, vista, **kwargs):
        try:
            # ``dispatch`` runs the native guards (login, extra permission, 404).
            # pylint: disable-next=protected-access
            respuesta = vista.dispatch(request._request, **kwargs)
        except Http404 as exc:
            raise NotFound() from exc
        if respuesta.status_code == 302:
            return Response({"ok": True, "redirect": respuesta["Location"]})
        estado = 200 if request.method in ("GET", "HEAD") else 400
        return Response(
            self._datos(request, respuesta.context_data, **kwargs), status=estado
        )

    def get(self, request, **kwargs):
        return self._responder(request, self._vista(request, **kwargs), **kwargs)

    def post(self, request, **kwargs):
        # ``Request.content_type`` keeps the multipart boundary; Django strips it.
        # pylint: disable-next=protected-access
        if request._request.content_type not in FORMATOS:
            return Response({"detail": "Formato de solicitud no admitido."}, status=415)
        return self._responder(request, self._vista(request, **kwargs), **kwargs)


class RendicionNuevaWebView(_FormularioWebView):
    """``.../rendicioncuentasmensual/nuevo/<comedor_id>/``: ``rendicioncuentasmensual_form.html``."""

    def _vista(self, request, **kwargs):
        return self.native(RendicionCuentaMensualCreateView, request, **kwargs)

    def _datos(self, request, contexto, **kwargs):
        comedor_id = kwargs["comedor_id"]
        form = contexto["form"]
        adjunta = contexto["documentacion_adjunta_form"]
        return {
            "comedor_id": int(comedor_id),
            # ``{{ form.instance.id|default:"Crear" }}``: the page only creates.
            "titulo": "Crear",
            "campos": {
                "mes": _campo(form, "mes"),
                "anio": _campo(form, "anio"),
                "linea_programatica": _campo(form, "linea_programatica"),
                "estado": _campo(form, "estado"),
                "observaciones": _campo(form, "observaciones"),
                "nombre": _campo(adjunta, "nombre"),
                "archivo": _campo(adjunta, "archivo"),
            },
            "errors": _errores(form),
            "non_field_errors": [str(e) for e in form.non_field_errors()],
            "urls": {
                "listado": reverse("rendicioncuentasmensual_list", args=[comedor_id])
            },
            "messages": pending_messages(request),
        }

    def post(self, request, **kwargs):
        try:
            return super().post(request, **kwargs)
        except Comedor.DoesNotExist as exc:
            raise NotFound() from exc


class RendicionEditarWebView(_FormularioWebView):
    """``.../rendicioncuentasmensual/editar/<pk>/``: ``rendicioncuentasmensual_datos_form.html``."""

    def _vista(self, request, **kwargs):
        return self.native(RendicionCuentaMensualUpdateView, request, **kwargs)

    def _datos(self, request, contexto, **kwargs):
        form = contexto["form"]
        rendicion = form.instance
        return {
            "id": rendicion.pk,
            # ``{{ form.instance.numero_rendicion|default:form.instance.pk }}``.
            "numero": localize(rendicion.numero_rendicion or rendicion.pk),
            "campos": {
                nombre: _campo(form, nombre)
                for nombre in (
                    "convenio",
                    "numero_rendicion",
                    "periodo_inicio",
                    "periodo_fin",
                    "nombre",
                )
            },
            "errors": _errores(form),
            "non_field_errors": [str(e) for e in form.non_field_errors()],
            "urls": {
                "detalle": reverse(
                    "rendicioncuentasmensual_detail", args=[rendicion.pk]
                )
            },
            "messages": pending_messages(request),
        }


class RendicionBajaWebView(NativeWebView):
    """``.../rendicioncuentasmensual/eliminar/<pk>/``: the native soft-delete confirmation."""

    permission_classes = [WebGatePermission, requires_any(_RENDICION_PERM)]
    http_method_names = ["get", "post", "head"]

    def _vista(self, request, pk):
        vista = self.native(RendicionCuentaMensualDeleteView, request, pk=pk)
        try:
            vista.object = vista.get_object()
        except Http404 as exc:
            raise NotFound() from exc
        return vista

    def get(self, request, pk):
        vista = self._vista(request, pk)
        contexto = vista.get_context_data()
        return Response(
            confirmacion(
                contexto,
                reverse("rendicioncuentasmensual_detail", args=[pk]),
                request,
            )
        )

    def post(self, request, pk):
        vista = self._vista(request, pk)
        # pylint: disable-next=protected-access
        respuesta = vista.post(request._request)
        return Response({"ok": True, "redirect": respuesta["Location"]})
