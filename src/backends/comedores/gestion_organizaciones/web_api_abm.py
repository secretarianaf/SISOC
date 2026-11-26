"""Web API (G1 v1) of the Organizaciones ABM (O05.02).

``/api/web/comedores/organizaciones/`` runs the native views themselves:
``OrganizacionCreateView`` / ``OrganizacionUpdateView`` (``OrganizacionForm``
validation, ``form.save()``, the tipo-de-entidad reset and its warning),
``OrganizacionDeleteView`` (baja with its blocking reasons) and the two native
JSON endpoints (subtipos, CUIT check). React gets the real form's fields,
options, values and errors; it never rebuilds a rule. Access is today's:
``organizaciones.view_organizacion`` on the route, with no object scope (see
``docs/registro/decisiones/2026-11-10-2785-brechas-acceso-conservadas.md``).
Errors are the Django texts verbatim; Django messages travel in ``messages``.
"""

import json

from django.http import HttpResponseRedirect
from django.urls import reverse
from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import BasePermission
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.views import APIView

from core.decorators import _has_any_permissions
from core.soft_delete.view_helpers import build_delete_preview
from core.web_gate import WebGatePermission
from gestion_organizaciones.services.programas import motivo_que_impide_baja
from gestion_organizaciones.views import (
    OrganizacionCreateView,
    OrganizacionDeleteView,
    OrganizacionUpdateView,
    cuil_check_ajax,
    sub_tipo_entidad_ajax,
)
from gestion_organizaciones.web_api import _pending_messages

ABM_PERMS = ["organizaciones.view_organizacion"]
API = "/api/web/comedores/organizaciones/"


class OrganizacionAbmAccess(BasePermission):
    """Same rule as ``permissions_any_required(["organizaciones.view_organizacion"])``."""

    def has_permission(self, request, view):
        return _has_any_permissions(request.user, ABM_PERMS)


def _valor(bound):
    value = bound.value()
    if isinstance(value, (list, tuple, set)):
        return [str(v) for v in value]
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    return str(value)


def _opciones(field):
    choices = getattr(field, "choices", None)
    if choices is None:
        return None
    return [{"value": str(v), "label": str(label)} for v, label in choices]


def _campo(bound):
    field = bound.field
    widget = field.widget
    if bound.is_hidden:
        tipo = "hidden"
    elif getattr(widget, "allow_multiple_selected", False):
        tipo = "multiple"
    elif hasattr(field, "choices"):
        tipo = "select"
    else:
        tipo = widget.input_type or "text"
    return {
        "name": bound.name,
        "label": str(bound.label or ""),
        "type": tipo,
        "required": field.required,
        "help": str(field.help_text or ""),
        "value": _valor(bound),
        "options": _opciones(field),
        "errors": [str(e) for e in bound.errors],
        "attrs": {
            k: str(v)
            for k, v in widget.attrs.items()
            if k in ("maxlength", "minlength", "min", "max", "step", "placeholder")
        },
    }


def _formulario(form, organizacion_pk):
    """The real form's fields (in form order), options, values and errors."""
    cancelar = (
        reverse("organizacion_detalle", kwargs={"pk": organizacion_pk})
        if organizacion_pk
        else reverse("organizaciones")
    )
    return {
        "organizacion_id": organizacion_pk,
        "fields": [_campo(form[name]) for name in form.fields],
        "non_field_errors": [str(e) for e in form.non_field_errors()],
        "data": form.datos_formulario(),
        "subzonas": getattr(form, "subzonas_abordaje", None),
        "tipo_entidad_actual": form.instance.tipo_entidad_id,
        "urls": {
            "cancel": cancelar,
            "subtipos": f"{API}subtipos/",
            "cuil": f"{API}cuil/",
        },
    }


def _vista(clase, request, **kwargs):
    vista = clase()
    vista.setup(request, **kwargs)
    return vista


class _AbmView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [WebGatePermission, OrganizacionAbmAccess]
    renderer_classes = [JSONRenderer]

    @staticmethod
    def _django(request):
        return request._request  # pylint: disable=protected-access


class OrganizacionFormularioWebView(_AbmView):
    """``GET .../formulario/`` and ``.../<pk>/formulario/``: the native form."""

    http_method_names = ["get", "head"]

    def get(self, request, pk=None):
        django_request = self._django(request)
        if pk is None:
            vista = _vista(OrganizacionCreateView, django_request)
            vista.object = None
        else:
            vista = _vista(OrganizacionUpdateView, django_request, pk=pk)
            vista.object = vista.get_object()
        form = vista.get_context_data()["form"]
        return Response(
            {
                "form": _formulario(form, pk),
                "messages": _pending_messages(django_request),
            }
        )


class OrganizacionGuardarWebView(_AbmView):
    """``POST .../crear/`` (201) and ``.../<pk>/editar/`` (200): the native ``post``."""

    http_method_names = ["post"]

    def post(self, request, pk=None):
        django_request = self._django(request)
        if pk is None:
            vista = _vista(OrganizacionCreateView, django_request)
        else:
            vista = _vista(OrganizacionUpdateView, django_request, pk=pk)
        respuesta = vista.post(django_request)
        if isinstance(respuesta, HttpResponseRedirect):
            return Response(
                {
                    "redirect": respuesta.url,
                    "messages": _pending_messages(django_request),
                },
                status=status.HTTP_201_CREATED if pk is None else status.HTTP_200_OK,
            )
        form = respuesta.context_data["form"]
        return Response(
            {
                "errors": {
                    name: [str(e) for e in errores]
                    for name, errores in form.errors.items()
                    if name != "__all__"
                },
                "non_field_errors": [str(e) for e in form.non_field_errors()],
                "form": _formulario(form, pk),
            },
            status=status.HTTP_400_BAD_REQUEST,
        )


class OrganizacionBajaWebView(_AbmView):
    """``GET/POST .../<pk>/baja/``: the native ``OrganizacionDeleteView``."""

    http_method_names = ["get", "head", "post"]

    def _baja(self, request, pk):
        vista = _vista(OrganizacionDeleteView, self._django(request), pk=pk)
        vista.object = vista.get_object()
        return vista

    def get(self, request, pk):
        organizacion = self._baja(request, pk).object
        return Response(
            {
                "id": organizacion.pk,
                "nombre": organizacion.nombre,
                "cascade_preview": build_delete_preview(organizacion),
                "motivo": motivo_que_impide_baja(organizacion),
                "urls": {
                    "cancel": reverse("organizacion_detalle", kwargs={"pk": pk}),
                    "list": reverse("organizaciones"),
                },
                "messages": _pending_messages(self._django(request)),
            }
        )

    def post(self, request, pk):
        django_request = self._django(request)
        respuesta = self._baja(request, pk).post(django_request)
        mensajes = _pending_messages(django_request)
        if isinstance(respuesta, HttpResponseRedirect):
            return Response({"redirect": respuesta.url, "messages": mensajes})
        # The native page re-renders the confirmation with the error message.
        return Response(
            {
                "error": mensajes[-1]["message"] if mensajes else "",
                "messages": mensajes,
            },
            status=status.HTTP_409_CONFLICT,
        )


class _JsonNativo(_AbmView):
    """Serves a native ``JsonResponse`` view unchanged."""

    http_method_names = ["get", "head"]
    nativa = None

    def get(self, request):
        respuesta = self.nativa(self._django(request))  # pylint: disable=not-callable
        return Response(json.loads(respuesta.content), status=respuesta.status_code)


class OrganizacionSubtiposWebView(_JsonNativo):
    """``GET .../subtipos/?tipo_entidad=``: ``sub_tipo_entidad_ajax``."""

    nativa = staticmethod(sub_tipo_entidad_ajax)


class OrganizacionCuilWebView(_JsonNativo):
    """``GET .../cuil/?cuil=&exclude=``: ``cuil_check_ajax``."""

    nativa = staticmethod(cuil_check_ajax)
