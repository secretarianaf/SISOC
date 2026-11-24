"""Web API (G1 v1) of the comedor observation screens served by React (CO06).

``/api/web/comedores/observaciones/`` is published by the Comedores backend. After G1
(``WebGatePermission``) each endpoint keeps the permission code of its native URL
(``comedores.add/view/change/delete_observacion``, superuser bypass included) and runs
the native view itself (``comedores.views.observacion``): the form, the user scope
(``get_scoped_comedor_or_404`` / ``get_scoped_comedor_queryset``), the server-side author
and date, ``safe_redirect`` with ``next`` and the soft delete with its message stay the
native ones. A native redirect becomes ``{"ok": true, "redirect": ...}``; an invalid
form returns 400 with its errors. Native quirk kept: editing replaces the visible
author and date with the editor and now (the view does it, not this module).

The native 500 for an observation outside the scope on the detail page (``.get`` on a
filtered ``values()`` queryset) is a 404 here.
"""

from django.core.exceptions import ObjectDoesNotExist
from django.http import Http404
from django.template import Context, Template
from django.urls import reverse
from rest_framework.exceptions import NotFound
from rest_framework.response import Response

from comedores.views.observacion import (
    ObservacionCreateView,
    ObservacionDeleteView,
    ObservacionDetailView,
    ObservacionUpdateView,
)
from core.web_gate import WebGatePermission
from intervenciones.web_api import NativeWebView, pending_messages, requires_any
from intervenciones.web_api_baja import confirmacion

FORMATOS = ("multipart/form-data", "application/x-www-form-urlencoded")
# ``{{ observacion.fecha_visita }}`` of the template: localized and in local time.
_FECHA = Template("{{ valor }}")


def _comedor(comedor_id, nombre):
    return {
        "id": comedor_id,
        "nombre": nombre,
        "url": reverse("comedor_detalle", args=[comedor_id]),
    }


def _formulario(contexto, request, observacion_id):
    form = contexto["form"]
    campo = form.fields["observacion"]
    attrs = campo.widget.attrs
    return {
        "comedor": _comedor(contexto["comedor"]["id"], contexto["comedor"]["nombre"]),
        "observacion_id": observacion_id,
        "urls": {
            "comedores": reverse("comedores"),
            "observacion": (
                reverse("observacion_detalle", args=[observacion_id])
                if observacion_id
                else None
            ),
        },
        "field": {
            "name": "observacion",
            "label": str(campo.label),
            "required": campo.required,
            "rows": int(attrs.get("rows", 4)),
            "placeholder": str(attrs.get("placeholder", "")),
        },
        "value": form["observacion"].value() or "",
        "errors": form.errors.get_json_data() if form.is_bound else {},
        "messages": pending_messages(request),
    }


class _FormularioWebView(NativeWebView):
    http_method_names = ["get", "post", "head"]

    def _vista(self, request, **kwargs):
        raise NotImplementedError

    def _id(self, vista):
        return getattr(getattr(vista, "object", None), "id", None)

    def get(self, request, **kwargs):
        vista = self._vista(request, **kwargs)
        try:
            contexto = vista.get_context_data()
        except Http404 as exc:
            raise NotFound() from exc
        return Response(_formulario(contexto, request, self._id(vista)))

    def post(self, request, **kwargs):
        # ``Request.content_type`` keeps the multipart boundary; Django strips it.
        # pylint: disable-next=protected-access
        if request._request.content_type not in FORMATOS:
            return Response({"detail": "Formato de solicitud no admitido."}, status=415)
        vista = self._vista(request, **kwargs)
        try:
            # pylint: disable-next=protected-access
            respuesta = vista.post(request._request)
            if respuesta.status_code == 302:
                return Response({"ok": True, "redirect": respuesta["Location"]})
            contexto = respuesta.context_data
        except Http404 as exc:
            raise NotFound() from exc
        return Response(_formulario(contexto, request, self._id(vista)), status=400)


class ObservacionCrearWebView(_FormularioWebView):
    """``/api/web/comedores/observaciones/comedor/<comedor_pk>/crear/``."""

    permission_classes = [
        WebGatePermission,
        requires_any(["comedores.add_observacion"]),
    ]

    def _vista(self, request, **kwargs):
        vista = self.native(ObservacionCreateView, request, **kwargs)
        vista.object = None
        return vista


class ObservacionEditarWebView(_FormularioWebView):
    """``/api/web/comedores/observaciones/<pk>/editar/``."""

    permission_classes = [
        WebGatePermission,
        requires_any(["comedores.change_observacion"]),
    ]

    def _vista(self, request, **kwargs):
        vista = self.native(ObservacionUpdateView, request, **kwargs)
        try:
            vista.object = vista.get_object()
        except Http404 as exc:
            raise NotFound() from exc
        return vista


class ObservacionDetalleWebView(NativeWebView):
    """``GET /api/web/comedores/observaciones/<pk>/``: the native detail card."""

    permission_classes = [
        WebGatePermission,
        requires_any(["comedores.view_observacion"]),
    ]

    def get(self, request, pk):
        vista = self.native(ObservacionDetailView, request, pk=pk)
        try:
            observacion = vista.get_object()
        except ObjectDoesNotExist as exc:
            raise NotFound() from exc
        return Response(
            {
                "id": observacion["id"],
                "comedor": _comedor(
                    observacion["comedor__id"], observacion["comedor__nombre"]
                ),
                "observador": str(observacion["observador"]),
                "fecha": _FECHA.render(Context({"valor": observacion["fecha_visita"]})),
                "observacion": observacion["observacion"],
                "urls": {
                    "comedores": reverse("comedores"),
                    "editar": reverse("observacion_editar", args=[pk]),
                    "eliminar": reverse("observacion_eliminar", args=[pk]),
                },
                "messages": pending_messages(request),
            }
        )


class ObservacionBajaWebView(NativeWebView):
    """``/api/web/comedores/observaciones/<pk>/eliminar/``: native soft-delete confirm."""

    permission_classes = [
        WebGatePermission,
        requires_any(["comedores.delete_observacion"]),
    ]
    http_method_names = ["get", "post", "head"]

    def _vista(self, request, pk):
        vista = self.native(ObservacionDeleteView, request, pk=pk)
        try:
            vista.object = vista.get_object()
        except Http404 as exc:
            raise NotFound() from exc
        return vista

    def get(self, request, pk):
        vista = self._vista(request, pk)
        contexto = vista.get_context_data()
        observacion = vista.object
        return Response(
            {
                **confirmacion(
                    {**contexto, "object": observacion},
                    reverse("observacion_detalle", args=[pk]),
                    request,
                ),
                "comedor": _comedor(observacion.comedor.id, observacion.comedor.nombre),
                "urls": {"comedores": reverse("comedores")},
            }
        )

    def post(self, request, pk):
        vista = self._vista(request, pk)
        # pylint: disable-next=protected-access
        respuesta = vista.post(request._request)
        return Response({"ok": True, "redirect": respuesta["Location"]})
