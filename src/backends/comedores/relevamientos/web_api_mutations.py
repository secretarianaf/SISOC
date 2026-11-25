"""Mutations of the relevamiento pages served by React (R01.02), G1 v1.

Every endpoint repeats the native rule of the view it replaces and reuses its
code: the Numero de IF update runs ``RelevamientoListView.post``, the baja runs
``RelevamientoDeleteView`` (``SoftDeleteDeleteViewMixin``) and the coordinator
review runs the same transaction, row lock and ``aplicar_revision_coordinador``
as ``RelevamientoRevisionCoordinadorView``. Each route checks its native
permission and the user's scope over the comedor. Success is
``{"ok": true, "message", "redirect"}``; errors are
``{"detail"}`` (403, 409) or ``{"errors": ...}`` (400), as in the contract.
"""

from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse
from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import NotFound
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import BasePermission
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.views import APIView

# The exact predicate of ``permissions_any_required``, the native URL guard.
from core.decorators import _has_any_permissions
from core.web_gate import WebGatePermission
from relevamientos.models import Relevamiento
from relevamientos.views.seguimiento_helpers import aplicar_revision_coordinador
from relevamientos.views.web_views import RelevamientoDeleteView, RelevamientoListView
from relevamientos.web_api_serializers import mostrar, pending_messages
from relevamientos.web_api_views import (
    RelevamientoAccess,
    _ComedorScopeMixin,
    _NativeReadView,
)

CHANGE_PERMISSIONS = ["relevamientos.change_relevamiento"]
REVIEW_PERMISSIONS = ["relevamientos.review_relevamiento"]
SIN_PERMISO_IF = "No tiene permisos para editar el Número de IF."


class RelevamientoChangeAccess(BasePermission):
    """Same rule as the native ``permissions_any_required(["relevamientos.change_relevamiento"])``."""

    def has_permission(self, request, view):
        return _has_any_permissions(request.user, CHANGE_PERMISSIONS)


class RelevamientoReviewAccess(BasePermission):
    """Same rule as the native ``permissions_any_required(["relevamientos.review_relevamiento"])``."""

    def has_permission(self, request, view):
        return _has_any_permissions(request.user, REVIEW_PERMISSIONS)


class _MutationView(_ComedorScopeMixin, APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [WebGatePermission, RelevamientoAccess]
    renderer_classes = [JSONRenderer]
    parser_classes = [FormParser, MultiPartParser]
    http_method_names = ["post", "options"]


def error_all(message, code="invalid"):
    """``{"errors": {"__all__": [{"message", "code"}]}}`` as ``form.errors.get_json_data()``."""
    return {"errors": {"__all__": [{"message": message, "code": code}]}}


def aplicar_revision(django_request, registro, etiqueta, mensaje_validado=None):
    """Runs the native review helper and maps its text to a status (D10).

    Returns ``(status, body)``: 409 when the record is already validated or
    still unsent (the same predicates, in the same order, as the helper), 400
    for the invalid result or a missing observation.
    """
    error = aplicar_revision_coordinador(
        django_request, registro, etiqueta, mensaje_validado
    )
    if not error:
        return None
    if registro.esta_validado or getattr(registro, "sin_cargar", False):
        return status.HTTP_409_CONFLICT, {"detail": error}
    return status.HTTP_400_BAD_REQUEST, error_all(error)


class NumeroIfWebView(_MutationView):
    """``POST .../<comedor_pk>/relevamiento/numero-if/``: ``RelevamientoListView.post``."""

    def post(self, request, comedor_pk):
        django_request = request._request  # pylint: disable=protected-access
        # Same check as the native view, before anything is read or written.
        if not request.user.has_perm("relevamientos.change_relevamiento"):
            return Response(
                {"detail": SIN_PERMISO_IF}, status=status.HTTP_403_FORBIDDEN
            )
        numero_if = (request.data.get("numero_if") or "").strip()
        try:
            Relevamiento._meta.get_field("numero_if").run_validators(numero_if)
        except ValidationError as exc:
            return Response(
                {
                    "errors": {
                        "numero_if": [
                            {"message": m, "code": e.code}
                            for e in exc.error_list
                            for m in e.messages
                        ]
                    }
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        vista = RelevamientoListView()
        vista.setup(django_request, comedor_pk=comedor_pk)
        vista.post(django_request, comedor_pk=comedor_pk)
        mensajes = pending_messages(django_request)
        return Response(
            {
                "ok": True,
                "message": mensajes[-1]["message"] if mensajes else "",
                "redirect": reverse("relevamientos", args=[comedor_pk]),
                "numero_if": numero_if or None,
            }
        )


class RelevamientoBajaWebView(_NativeReadView):
    """``GET/POST .../<comedor_pk>/relevamiento/<pk>/eliminar/``: ``RelevamientoDeleteView``."""

    permission_classes = [WebGatePermission, RelevamientoChangeAccess]
    parser_classes = [FormParser, MultiPartParser]
    http_method_names = ["get", "head", "post", "options"]

    def _vista(self, request, comedor_pk, pk):
        vista = self.native(
            RelevamientoDeleteView, request, comedor_pk=comedor_pk, pk=pk
        )
        try:
            vista.object = vista.get_object()
        except Http404 as exc:
            raise NotFound() from exc
        return vista

    def get(self, request, comedor_pk, pk):
        django_request = request._request  # pylint: disable=protected-access
        vista = self._vista(request, comedor_pk, pk)
        context = vista.get_context_data(object=vista.object)
        relevamiento = vista.object
        return Response(
            {
                "id": relevamiento.id,
                "nombre": str(relevamiento),
                "comedor": {
                    "id": relevamiento.comedor.id,
                    "nombre": relevamiento.comedor.nombre,
                },
                "fecha_visita": mostrar(relevamiento.fecha_visita, "Sin información"),
                "cascade_preview": context.get("cascade_preview"),
                "confirm_text": context["confirm_text"],
                "cancel_text": context["cancel_text"],
                "cancel_url": reverse(
                    "relevamiento_detalle",
                    args=[relevamiento.comedor.id, relevamiento.id],
                ),
                "urls": {"comedores": reverse("comedores")},
                "messages": pending_messages(django_request),
            }
        )

    def post(self, request, comedor_pk, pk):
        django_request = request._request  # pylint: disable=protected-access
        _ = request.data
        vista = self._vista(request, comedor_pk, pk)
        respuesta = vista.post(django_request, comedor_pk=comedor_pk, pk=pk)
        if isinstance(respuesta, HttpResponseRedirect):
            # The success message stays queued: the comedor page it redirects to shows it.
            return Response(
                {
                    "ok": True,
                    "message": vista.success_message,
                    "redirect": respuesta.url,
                }
            )
        return Response(
            {"detail": "No se pudo dar de baja el acompañamiento territorial."},
            status=status.HTTP_409_CONFLICT,
        )


class RelevamientoRevisionWebView(_MutationView):
    """``POST .../<comedor_pk>/relevamiento/<pk>/revision/``: ``RelevamientoRevisionCoordinadorView``."""

    permission_classes = [WebGatePermission, RelevamientoReviewAccess]

    def post(self, request, comedor_pk, pk):
        django_request = request._request  # pylint: disable=protected-access
        # DRF parsed the body into ``request.data``; the native helper reads ``POST``.
        _ = request.data
        with transaction.atomic():
            # Row lock, as in the native view: no crossing with the territorial's correction.
            relevamiento = get_object_or_404(
                Relevamiento.objects.select_for_update(), pk=pk, comedor_id=comedor_pk
            )
            fallo = aplicar_revision(
                django_request, relevamiento, "el acompañamiento territorial"
            )
        if fallo:
            return Response(fallo[1], status=fallo[0])
        if relevamiento.estado_validacion == Relevamiento.ESTADO_VALIDACION_VALIDADO:
            mensaje = "Acompañamiento Territorial validado correctamente."
        else:
            mensaje = (
                "Acompañamiento Territorial devuelto al territorial para subsanar."
            )
        return Response(
            {
                "ok": True,
                "message": mensaje,
                "redirect": reverse(
                    "relevamiento_detalle",
                    kwargs={"comedor_pk": comedor_pk, "pk": pk},
                ),
            }
        )
