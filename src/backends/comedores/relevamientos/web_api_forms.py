"""Edit, delete and review endpoints of seguimientos, PNUD and actas (R03.02, R02.02), G1 v1.

Every write goes through the native code: the edit forms are the native
``SeguimientoEditor`` / ``ActaComplementariaEditor`` (validation, row creation
rules and ``@transaction.atomic`` saves), the deletes are the native
``PrimerSeguimientoEliminarView`` / ``ActaComplementariaEliminarView`` (cascade
and the GESTIONAR baja signal) and the reviews repeat the native transaction,
row lock and ``aplicar_revision_coordinador`` (mapped to 400/409 by
``web_api_mutations.aplicar_revision``). The forms are projected as the real
widget markup (``web_api_serializers.campo``), with their bound errors, so
React never rebuilds a field or a rule. Access is today's: the route
permission of each native URL, no object scope other than the URL's own comedor
and relevamiento (see
``docs/registro/decisiones/2026-11-10-2785-brechas-acceso-conservadas.md``).
Success is ``{"ok": true, "message", "redirect"}``; an invalid form is a 400
with ``detail`` and the bound descriptors.
"""

from django.db import transaction
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse
from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.permissions import BasePermission
from rest_framework.response import Response

# The exact predicate of ``permissions_any_required``, the native URL guard.
from core.decorators import _has_any_permissions
from core.web_gate import WebGatePermission
from comedores.models import Comedor
from relevamientos.forms_backoffice import ActaComplementariaEditor, SeguimientoEditor
from relevamientos.models import ActaComplementaria, PrimerSeguimiento, SeguimientoPnud
from relevamientos.views.backoffice_views import (
    ActaComplementariaEliminarView,
    _url_detalle_seguimiento,
    _url_detalle_seguimiento_pnud,
)
from relevamientos.views.seguimiento_helpers import (
    resolver_seguimiento,
    seguimiento_queryset,
)
from relevamientos.views.web_views import PrimerSeguimientoEliminarView
from relevamientos.web_api_mutations import _MutationView, aplicar_revision
from relevamientos.web_api_serializers import (
    FORM_ERROR,
    editor_acta,
    editor_seguimiento,
    mostrar,
    pending_messages,
)
from relevamientos.web_api_views import _NativeReadView


def acceso(*codes):
    """A permission class with the same rule as ``permissions_any_required(codes)``."""

    class Acceso(BasePermission):
        def has_permission(self, request, view):
            return _has_any_permissions(request.user, list(codes))

    return Acceso


def _django(request):
    return request._request  # pylint: disable=protected-access


def _invalido(cuerpo):
    return Response(
        {"detail": FORM_ERROR, **cuerpo}, status=status.HTTP_400_BAD_REQUEST
    )


def _ok(mensaje, redirect):
    return Response({"ok": True, "message": mensaje, "redirect": redirect})


def _urls_seguimiento(seguimiento):
    relevamiento = seguimiento.id_relevamiento
    comedor = relevamiento.comedor
    return {
        "comedores": reverse("comedores"),
        "comedor": reverse("comedor_detalle", args=[comedor.id]),
        "relevamiento": reverse(
            "relevamiento_detalle", args=[comedor.id, relevamiento.id]
        ),
        "detalle": _url_detalle_seguimiento(seguimiento),
    }


def _cabecera_seguimiento(seguimiento):
    relevamiento = seguimiento.id_relevamiento
    return {
        "seguimiento": {
            "id": seguimiento.id,
            "tipo_display": seguimiento.get_tipo_display(),
            "numero_orden": seguimiento.numero_orden,
        },
        "relevamiento": {
            "id": relevamiento.id,
            "fecha_visita": mostrar(relevamiento.fecha_visita, "Sin información"),
        },
        "comedor": {
            "id": relevamiento.comedor.id,
            "nombre": relevamiento.comedor.nombre,
        },
        "urls": _urls_seguimiento(seguimiento),
    }


# --- Seguimiento -----------------------------------------------------------------


class SeguimientoEditarWebView(_NativeReadView):
    """``GET/POST .../seguimientos/<pk>/editar/``: ``SeguimientoUpdateView``."""

    permission_classes = [
        WebGatePermission,
        acceso("relevamientos.change_primerseguimiento"),
    ]
    http_method_names = ["get", "head", "post", "options"]

    def _seguimiento(self, comedor_pk, relevamiento_pk, pk):
        try:
            return resolver_seguimiento(
                {
                    "comedor_pk": comedor_pk,
                    "relevamiento_pk": relevamiento_pk,
                    "pk": pk,
                },
                seguimiento_queryset(),
            )
        except Http404 as exc:
            raise NotFound() from exc

    def get(self, request, comedor_pk, relevamiento_pk, pk):
        seguimiento = self._seguimiento(comedor_pk, relevamiento_pk, pk)
        return Response(
            {
                **_cabecera_seguimiento(seguimiento),
                **editor_seguimiento(SeguimientoEditor(seguimiento)),
                "messages": pending_messages(_django(request)),
            }
        )

    def post(self, request, comedor_pk, relevamiento_pk, pk):
        seguimiento = self._seguimiento(comedor_pk, relevamiento_pk, pk)
        django_request = _django(request)
        _ = request.data  # DRF parses the body into ``POST`` for the native editor
        editor = SeguimientoEditor(seguimiento, data=django_request.POST)
        if not editor.es_valido():
            return _invalido(
                {**_cabecera_seguimiento(seguimiento), **editor_seguimiento(editor)}
            )
        editor.guardar()
        return _ok(
            "Seguimiento actualizado correctamente.",
            _url_detalle_seguimiento(seguimiento),
        )


class SeguimientoEliminarWebView(_MutationView):
    """``POST .../seguimientos/<pk>/eliminar/`` (and ``primero/``): ``PrimerSeguimientoEliminarView``."""

    permission_classes = [
        WebGatePermission,
        acceso("relevamientos.delete_primerseguimiento"),
    ]

    def post(self, request, comedor_pk, relevamiento_pk, pk=None):
        django_request = _django(request)
        kwargs = {"comedor_pk": comedor_pk, "relevamiento_pk": relevamiento_pk}
        if pk is not None:
            kwargs["pk"] = pk
        vista = PrimerSeguimientoEliminarView()
        vista.setup(django_request, **kwargs)
        try:
            respuesta = vista.post(django_request, **kwargs)
        except Http404 as exc:
            raise NotFound() from exc
        # The page it redirects to is React: the message travels in the answer, not the queue.
        mensajes = pending_messages(django_request)
        return _ok(
            mensajes[-1]["message"] if mensajes else "", _redirect_url(respuesta)
        )


def _redirect_url(respuesta):
    """The native views answer a redirect; its URL is the screen to go to."""
    if not isinstance(respuesta, HttpResponseRedirect):
        raise NotFound()
    return respuesta.url


class SeguimientoRevisionWebView(_MutationView):
    """``POST .../seguimientos/<pk>/revision/``: ``SeguimientoRevisionCoordinadorView``."""

    permission_classes = [
        WebGatePermission,
        acceso("relevamientos.review_relevamiento"),
    ]

    def post(self, request, comedor_pk, relevamiento_pk, pk):
        django_request = _django(request)
        _ = request.data
        with transaction.atomic():
            try:
                seguimiento = resolver_seguimiento(
                    {
                        "comedor_pk": comedor_pk,
                        "relevamiento_pk": relevamiento_pk,
                        "pk": pk,
                    },
                    PrimerSeguimiento.objects.select_for_update(),
                )
            except Http404 as exc:
                raise NotFound() from exc
            fallo = aplicar_revision(django_request, seguimiento, "el seguimiento")
        if fallo:
            return Response(fallo[1], status=fallo[0])
        if seguimiento.estado_validacion == seguimiento.ESTADO_VALIDACION_VALIDADO:
            mensaje = "Seguimiento validado correctamente."
        else:
            mensaje = "Seguimiento devuelto al territorial para subsanar."
        return _ok(mensaje, _url_detalle_seguimiento(seguimiento))


class PnudRevisionWebView(_MutationView):
    """``POST .../pnud/<pk>/revision/``: ``SeguimientoPnudRevisionCoordinadorView``."""

    permission_classes = [
        WebGatePermission,
        acceso("relevamientos.review_relevamiento"),
    ]

    def post(self, request, comedor_pk, pk):
        django_request = _django(request)
        _ = request.data
        with transaction.atomic():
            seguimiento = get_object_or_404(
                SeguimientoPnud.objects.select_for_update(),
                pk=pk,
                comedor_id=comedor_pk,
            )
            fallo = aplicar_revision(django_request, seguimiento, "el seguimiento PNUD")
            if not fallo:
                # The shared helper saves with ``update_fields`` without ``auto_now``.
                seguimiento.save(update_fields=["fecha_actualizacion"])
        if fallo:
            return Response(fallo[1], status=fallo[0])
        if seguimiento.esta_validado:
            mensaje = "Seguimiento PNUD validado correctamente."
        else:
            mensaje = "Seguimiento PNUD devuelto al territorial para subsanar."
        return _ok(mensaje, _url_detalle_seguimiento_pnud(seguimiento))


# --- Acta complementaria ---------------------------------------------------------


class _ActaFormularioWebView(_NativeReadView):
    http_method_names = ["get", "head", "post", "options"]

    def _cargar(self, comedor_pk, pk):
        comedor = get_object_or_404(Comedor, pk=comedor_pk)
        acta = None
        if pk is not None:
            acta = get_object_or_404(
                ActaComplementaria.objects.prefetch_related("prestaciones"),
                pk=pk,
                comedor=comedor,
            )
        return comedor, acta

    def _cuerpo(self, comedor, acta, editor):
        return {
            "acta_id": acta.id if acta else None,
            "comedor": {"id": comedor.id, "nombre": comedor.nombre},
            **editor_acta(editor),
            "urls": {
                "comedores": reverse("comedores"),
                "comedor": reverse("comedor_detalle", args=[comedor.id]),
                "listado": reverse("relevamientos", args=[comedor.id]),
            },
        }

    def get(self, request, comedor_pk, pk=None):
        try:
            comedor, acta = self._cargar(comedor_pk, pk)
        except Http404 as exc:
            raise NotFound() from exc
        return Response(
            {
                **self._cuerpo(comedor, acta, ActaComplementariaEditor(comedor, acta)),
                "messages": pending_messages(_django(request)),
            }
        )

    def post(self, request, comedor_pk, pk=None):
        try:
            comedor, acta = self._cargar(comedor_pk, pk)
        except Http404 as exc:
            raise NotFound() from exc
        django_request = _django(request)
        _ = request.data
        editor = ActaComplementariaEditor(comedor, acta, data=django_request.POST)
        if not editor.es_valido():
            return _invalido(self._cuerpo(comedor, acta, editor))
        guardada = editor.guardar(django_request.user)
        return _ok(
            "Acta complementaria guardada correctamente.",
            reverse(
                "acta_complementaria_detalle",
                kwargs={"comedor_pk": comedor.pk, "pk": guardada.pk},
            ),
        )


class ActaCrearWebView(_ActaFormularioWebView):
    """``GET/POST .../actas/crear/``: ``ActaComplementariaFormView`` without ``pk``."""

    permission_classes = [
        WebGatePermission,
        acceso("relevamientos.add_actacomplementaria"),
    ]


class ActaEditarWebView(_ActaFormularioWebView):
    """``GET/POST .../actas/<pk>/editar/``: ``ActaComplementariaFormView`` with ``pk``."""

    permission_classes = [
        WebGatePermission,
        acceso("relevamientos.change_actacomplementaria"),
    ]


class ActaRevisionWebView(_MutationView):
    """``POST .../actas/<pk>/revision/``: ``ActaComplementariaRevisionCoordinadorView``."""

    permission_classes = [
        WebGatePermission,
        acceso("relevamientos.review_relevamiento"),
    ]

    def post(self, request, comedor_pk, pk):
        django_request = _django(request)
        _ = request.data
        with transaction.atomic():
            acta = get_object_or_404(
                ActaComplementaria.objects.select_for_update(),
                pk=pk,
                comedor_id=comedor_pk,
            )
            fallo = aplicar_revision(
                django_request,
                acta,
                "el acta complementaria",
                mensaje_validado=(
                    "El acta complementaria ya está validada: no admite otra "
                    "revisión."
                ),
            )
        if fallo:
            return Response(fallo[1], status=fallo[0])
        if acta.esta_validado:
            mensaje = "Acta complementaria validada correctamente."
        else:
            mensaje = "Acta complementaria devuelta al territorial para subsanar."
        return _ok(
            mensaje,
            reverse(
                "acta_complementaria_detalle",
                kwargs={"comedor_pk": comedor_pk, "pk": pk},
            ),
        )


class ActaEliminarWebView(_MutationView):
    """``POST .../actas/<pk>/eliminar/``: ``ActaComplementariaEliminarView``."""

    permission_classes = [
        WebGatePermission,
        acceso("relevamientos.delete_actacomplementaria"),
    ]

    def post(self, request, comedor_pk, pk):
        django_request = _django(request)
        vista = ActaComplementariaEliminarView()
        vista.setup(django_request, comedor_pk=comedor_pk, pk=pk)
        try:
            respuesta = vista.post(django_request, comedor_pk=comedor_pk, pk=pk)
        except Http404 as exc:
            raise NotFound() from exc
        mensajes = pending_messages(django_request)
        return _ok(
            mensajes[-1]["message"] if mensajes else "", _redirect_url(respuesta)
        )
