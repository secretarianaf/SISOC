"""Web API (G1 v1) of the comedor intervention screens served by React (CO02).

``/api/web/comedores/intervenciones/`` is published by the Comedores backend.
In a split deploy the core checks the session and the web prerequisites and
signs each request; in the monolith ``WebGatePermission`` evaluates the same
policy locally. After that each endpoint keeps the exact permission codes of
the native URL (``comedores/urls.py``, superuser bypass included) and runs the
native view itself (``setup()``, filters, ``get_context_data()``); this module
only projects that context to JSON. No scope is added: like the native routes,
the intervention list and detail are not restricted to the user's comedores.

Native quirks kept on purpose: an unknown comedor or intervention is a 404
(natively a 500 for the comedor and the framework 404 for the intervention);
``None`` catalog values render as the text ``None`` as in the template.
"""

from django.contrib import messages
from django.http import Http404
from django.template.defaultfilters import date as date_filter
from django.urls import reverse
from django.utils import timezone
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import NotFound
from rest_framework.permissions import BasePermission
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.views import APIView

from comedores.models import Comedor
from core.decorators import _has_any_permissions
from core.web_gate import WebGatePermission
from intervenciones.views import (
    IntervencionDetailIndividualView,
    IntervencionDetailView,
    eliminar_archivo_intervencion,
)

PERMISOS_VER = ["intervenciones.view_intervencion"]
# The exact codes of the native ``eliminar_archivo_intervencion`` URL.
PERMISOS_ARCHIVO = [
    "comedores.view_comedor",
    "admisiones.view_admision",
    "acompanamientos.view_informacionrelevante",
]
MESSAGE_LEVELS = {
    messages.DEBUG: "info",
    messages.INFO: "info",
    messages.SUCCESS: "success",
    messages.WARNING: "warning",
    messages.ERROR: "error",
}


def pending_messages(request):
    """Consume queued Django messages exactly as the native page would."""
    return [
        {"message": str(m), "level": MESSAGE_LEVELS.get(m.level, "info")}
        for m in messages.get_messages(request)
    ]


def requires_any(codes):
    """The predicate of ``permissions_any_required(codes)`` as a DRF permission."""

    class RequiresAny(BasePermission):
        def has_permission(self, request, view):
            return _has_any_permissions(request.user, codes)

    return RequiresAny


class NativeWebView(APIView):
    """Session JSON transport over a native view; subclasses set the permission."""

    authentication_classes = [SessionAuthentication]
    renderer_classes = [JSONRenderer]
    http_method_names = ["get", "head"]

    @staticmethod
    def native(view_class, request, **kwargs):
        vista = view_class()
        vista.setup(request._request, **kwargs)  # pylint: disable=protected-access
        return vista


def comedor_ref(comedor):
    return {
        "id": comedor.id,
        "nombre": comedor.nombre,
        "url": reverse("comedor_detalle", args=[comedor.id]),
    }


def _fecha(valor, formato):
    return date_filter(timezone.localtime(valor), formato)


def _fila(intervencion, comedor_id, es_superusuario):
    return {
        "id": intervencion.id,
        "fecha": _fecha(intervencion.fecha, "d/m/Y"),
        # The template prints ``{{ x }}``: a missing catalog value is "None".
        "tipo_intervencion": str(intervencion.tipo_intervencion),
        "subintervencion": str(intervencion.subintervencion),
        "destinatario": str(intervencion.destinatario),
        "forma_contacto": str(intervencion.forma_contacto),
        "tiene_documentacion": bool(intervencion.tiene_documentacion),
        "url": reverse("intervencion_detalle", args=[intervencion.id]),
        "url_eliminar": (
            reverse("comedor_intervencion_borrar", args=[comedor_id, intervencion.id])
            if es_superusuario
            else None
        ),
    }


class IntervencionesListadoWebView(NativeWebView):
    """``GET .../intervenciones/comedor/<pk>/``: ``intervencion_detail.html``."""

    permission_classes = [WebGatePermission, requires_any(PERMISOS_VER)]

    def get(self, request, pk):
        vista = self.native(IntervencionDetailView, request, pk=pk)
        try:
            contexto = vista.get_context_data(pk=pk)
        except Comedor.DoesNotExist as exc:
            raise NotFound() from exc
        comedor = contexto["object"]
        es_superusuario = request.user.is_superuser
        consulta = request.GET
        return Response(
            {
                "comedor": comedor_ref(comedor),
                "admision_id": contexto["admision_id"],
                "admisiones": [
                    {
                        "id": adm.id,
                        "convenio": adm.acompanamiento.nro_convenio or None,
                        "activa": bool(adm.activa),
                    }
                    for adm in contexto["admisiones_disponibles"]
                ],
                "filtros": {
                    "fecha": consulta.get("fecha", ""),
                    "tipo_intervencion": consulta.get("tipo_intervencion", ""),
                    "destinatario": consulta.get("destinatario", ""),
                },
                "tipos_intervencion": [
                    {"id": t.id, "nombre": t.nombre}
                    for t in contexto["tipos_intervencion"]
                ],
                "destinatarios": [
                    {"id": d.id, "nombre": d.nombre} for d in contexto["destinatarios"]
                ],
                "results": [
                    _fila(i, comedor.id, es_superusuario)
                    for i in contexto["intervenciones"]
                ],
                "urls": {
                    "agregar": reverse("comedor_intervencion_crear", args=[comedor.id]),
                    "volver": reverse("comedor_detalle", args=[comedor.id]),
                },
                "messages": pending_messages(request),
            }
        )


class IntervencionDetalleWebView(NativeWebView):
    """``GET .../intervenciones/<pk>/``: ``intervencion_detail_view.html``."""

    permission_classes = [WebGatePermission, requires_any(PERMISOS_VER)]

    def get(self, request, pk):
        vista = self.native(IntervencionDetailIndividualView, request, pk=pk)
        try:
            contexto = vista.get_context_data(pk=pk)
        except Http404 as exc:
            raise NotFound() from exc
        intervencion = contexto["intervencion"]
        documentacion = intervencion.documentacion
        return Response(
            {
                "id": intervencion.id,
                "fecha": _fecha(intervencion.fecha, "d/m/Y H:i"),
                "tipo_intervencion": str(intervencion.tipo_intervencion),
                "subintervencion": str(intervencion.subintervencion),
                "forma_contacto": str(intervencion.forma_contacto),
                "observaciones": str(intervencion.observaciones),
                "documentacion": (
                    {"name": documentacion.name, "url": documentacion.url}
                    if documentacion
                    else None
                ),
                "puede_eliminar_archivo": request.user.is_superuser,
                "messages": pending_messages(request),
            }
        )


class ArchivoEliminarWebView(NativeWebView):
    """``POST .../intervenciones/<pk>/documentacion/eliminar/``: native action.

    Runs ``eliminar_archivo_intervencion`` (any signed-in user with one of the
    native permission codes, like the URL; the template only shows the button
    to superusers and that difference is kept). Its message is queued and the
    redirect to the detail becomes ``{"ok": true, "redirect": ...}``.
    """

    permission_classes = [WebGatePermission, requires_any(PERMISOS_ARCHIVO)]
    http_method_names = ["post"]

    def post(self, request, pk):
        try:
            # pylint: disable-next=protected-access
            respuesta = eliminar_archivo_intervencion(request._request, pk)
        except Http404 as exc:
            raise NotFound() from exc
        return Response({"ok": True, "redirect": respuesta["Location"]})
